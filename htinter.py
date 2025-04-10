"""
Serveur HTTP rudimentaire, destiné à la mise en place d'INTERface graphiques HyperTextuelles.

Le serveur fonctionne comme un serveur web pour tous les fichiers de l'arborescence du script sauf les fichiers .html (mais pas les .htm) pour lesquels il ajoute un éléments <script></script> avant la balise </head> (sensible à la casse) permettant à la page d'interagir de façon transparente avec lui.

Fonctions proposées.
  servir          : démarrer le serveur
  stop            : arrêter le serveur
  api             : associer un chemin d'accès à une fonction affectuant des actions.
  lier_param      : passer l'attribut value d'un objet en paramètre de toutes les actions déclenchées par la page html

Actions définissant un appel à une api.
  init_page       : définir une fonction à appeler à l'affichage de chaque page html
  capture_clic    : associer un événement au clic sur un objet
  écouter_touches : associer un événement aux touches du clavier (événement keyup)

Actions sans lien explicite avec une api.
  charge_page     : forcer la redirection de la page html affichée
  contenu         : changer l'attribut innerHtml d'un objet de la page
  valeur          : changer l'attrbut value d'un objet de la page
  classes         : changer l'attribut class d'un objet de la page

Actions sans lien explicite avec la page html.
  def_battement   : définir un appel cyclique à une fonction python qui agit sur la page html
  état_battement  : désactiver/réactiver un battement

Auteur : M. Bordonaro
"""

import socket
import json

_catalogue = {}  # associations chemins-callbacks

_battements = []  # liste des battements

_continuer = True  # passe à False pour quitter le serveur une fois que toutes les donnés du socket ont été purgées

_actions = {}  # l'objet à trasmettre en json en réponse à une requête


def servir(ip: str = '127.0.0.1', port: int = 5080, max_conn: int = -1) -> None:
    """
    appel bloquant démarrant un serveur sur le port 'port' de l'interface 'ip'
    si max_conn > 0, le serveur s'arrête après avoir répondu à max_conn requêtes
    """

    global _actions

    chemin_js = '/js'  # version future : pour personnaliser le javascript inséré, en changeant l'ordre des «comm ==»

    def interlocuteur_js() -> str:
        """
        renvoie le code javascript d'une fonction pour communiquer en xhr/json avec le serveur
        """
        return """window["__tictacs"] = {};
window["__params"] = {};
function namedNodeMapToObject(namedNodeMap) {
  const obj = {};
  for (let i = 0; i < namedNodeMap.length; i++) {
    const node = namedNodeMap[i];
    obj[node.nodeName] = node.nodeValue;
  }
  return obj;
}
function commande_api(api, commande) {
  let req = new XMLHttpRequest();
  let val_param = "";
  for (let param in window["__params"]) val_param += "&" + param + "=" + document.getElementById(window["__params"][param]).value;
  if (commande.length == 0) val_param = val_param.substring(1);
  req.open('GET', api + '?' + commande + val_param);
  req.onreadystatechange =
    function() {
      if (req.readyState == 4 && req.status == 200) {
        let rep = JSON.parse(req.responseText);
        if ("propage" in rep) document.location = rep["propage"];
        if ("params" in rep)
          for (let obj in rep["params"])
            if (document.getElementById(obj) != null) window["__params"][rep["params"][obj]] = obj;
        if ("contenu" in rep)
          for (let obj in rep["contenu"])
            document.querySelectorAll(obj).forEach(el => el.innerHTML = rep["contenu"][obj]);
        if ("alasuite" in rep)
          for (let obj in rep["alasuite"])
            document.querySelectorAll(obj).forEach(el => {
              for (cnt of rep["alasuite"][obj])
                el.innerHTML += cnt;
            });
        if ("classes" in rep)
          for (let obj in rep["classes"])
            document.querySelectorAll(obj).forEach(el => el.classList = rep["classes"][obj]);
        if ("valeurs" in rep)
          for (let obj in rep["valeurs"])
            document.querySelectorAll(obj).forEach(el => el.value = rep["valeurs"][obj]);
        if ("créer_batt" in rep)
          for (let ref in rep["créer_batt"])
            window["__tictacs"][ref] = window.setInterval(() => commande_api("/__tictac", "ref=" + ref), parseInt(rep["créer_batt"][ref]));
        if ("stop_batt" in rep)
          for (let ref of rep["stop_batt"])
            window.clearInterval(window["__tictacs"][ref]);
        if ("écouter_touches" in rep)
          if (rep["écouter_touches"]) document.body.onkeyup = function(a) { commande_api(rep["comm_touches"], "touche=" + a.key); };
          else document.body.onkeypress = undefined;
        if ("capture_clic" in rep)
          for (let taf of rep["capture_clic"])
            document.querySelectorAll(taf[1]).forEach(el => {
              if (taf[0]) el.onclick = () => {
                  let params = "objet=" + taf[1];
                  if (el.hasAttributes())
                    for (let attr of el.attributes)
                      params += "&" + attr.name + "=" + attr.value;
                  commande_api(taf[2], params)
              };
              else el.onclick = undefined;
            });
      }
    };
  req.send();
}
window.addEventListener("DOMContentLoaded", () => commande_api("/__init", "location_pathname=" + document.location.pathname));"""

    def pourcent_dec_get(burl: bytes) -> str:
        """
        pratique un url->utf-8, mais =, & et % restent %-encodés, et «+» n'est pas changé en « »
        """
        res = b''
        k = 0
        while k < len(burl):
            if burl[k] == b'%'[0]:
                if int(burl[k + 1 : k + 3], 16) in [0x3D, 0x26, 0x25]:
                    # c'est '&' ou '=' ou '%', on le garde pour la fin
                    res = res + burl[k : k + 3]
                else:
                    # on décode, sauf 3D et 26 et 25
                    res = res + bytes([int(burl[k + 1 : k + 3], 16)])
                k = k + 3
            # elif burl[k] == b'+'[0]:
            #    res = res + ' '
            else:
                res = res + bytes([burl[k]])
                k = k + 1
        return str(res, 'utf-8')

    def extraire(url: str) -> dict:
        """
        renvoie un dictionnaire construit à partir des paramètres passés par url
        """
        res = {}
        lc = url.split('&')
        for aff in lc:
            if '=' in aff:
                c, v = aff.split('=', 1)
            else:
                c = aff
                v = ''
            # on décode les «=» «&» et «%» qui étaient encore encodés
            c = (
                c.replace('%3D', '=')
                .replace('%3d', '=')
                .replace('%26', '&')
                .replace('%25', '%')
            )
            v = (
                v.replace('%3D', '=')
                .replace('%3d', '=')
                .replace('%26', '&')
                .replace('%25', '%')
            )
            res[c] = v

        return res

    def typemime(ext: str) -> bytes:
        """
        Renvoie le type mime associé à une extension.
        Catalogue les types mime les plus courants pour les applications visées,
        les autres contenus sont typés «application/octet-stream».
        """
        mime_b = {  # contenus binaire
            'png': b'image/png',
            'jpg': b'image/jpeg',
            'jpeg': b'image/jpeg',
            'gif': b'image/gif',
            'ico': b'image/x-icon',
        }
        mime_t = {  # contenus textuels
            'htm': b'text/html',
            'html': b'text/html',
            'css': b'text/css',
            'js': b'application/javascript',
            'csv': b'text/csv',
            'json': b'appliation/json',
            'svg': b'image/svg+xml',
            'xhtml': b'application/xhtml+xml',
            'xml': b'application/xml',
        }
        ext = ext.lower()  # on standardise l'extension
        if ext in mime_b:
            return mime_b[ext], False
        elif ext in mime_t:
            return mime_t[ext], True
        else:  # extension non reconnue
            return b'application/octet-stream', False

    def empaqueter(contenu: bytes, extension: str) -> bytes:
        """
        Génère un paquet HTTP à partir de contenu dont le type est donné par extension
        """
        type_mime, textuel = typemime(extension)
        if textuel:
            encodage = b'; charset=utf-8'
            if type(contenu) == type(''):
                contenu = bytes(contenu, 'utf-8')
        else:
            encodage = b''
        return (
            b'HTTP/1.1 200 OK\r\nContent-Type: '
            + type_mime
            + encodage
            + b'\r\nConnection: close\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: '
            + bytes(str(len(contenu)), 'utf-8')
            + b'\r\n\r\n'
            + contenu
        )

    def gen_fichier(comm: str) -> bytes:
        """
        génère un paquet HTTP à partir du chemin du fichier
        """
        extension = comm.split('.')[-1]
        try:
            with open(comm, 'rb') as fichier:
                contenu = fichier.read()
        except:  # s'il n'existe pas (ou autre erreur !)
            return bytes(
                'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain; charset=utf-8\r\nConnection: close\r\nContent-Length:17\r\n\r\nPas trouvé !\r\n\r\n',
                'utf-8',
            )
        else:
            if extension.lower() == 'html':
                contenu = contenu.replace(
                    b'</head>', b'<script src="/js"></script></head>'
                )
            return empaqueter(contenu, extension)

    # mise en place du socket «s» en écoute sur (ip, port)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, port))
    s.listen()

    print('Démarrage du serveur http://' + ip + ':' + str(port))

    # boucle du serveur : accepte les connexions sur s et y répond
    while _continuer and max_conn != 0:
        # on accepte la connexion
        t, (h, p) = s.accept()

        # on filtre les flux
        t.settimeout(0.05)

        try:
            req = t.recv(2048)
        except socket.timeout:
            pass
        #            print ('Timeout !')
        except:
            pass
        #            print ('Autre...')
        else:
            #            print('succès')

            max_conn = min(max_conn, max(max_conn - 1, 0))
            t.shutdown(socket.SHUT_RD)

            query = req.split(b'\r\n', 1)[0]
            elts = query.split(b' ')

            if elts[0] == b'GET':
                url = elts[1].split(b'?', 1)
                comm = pourcent_dec_get((url[0]))
                if len(url) == 1:
                    param = ''
                else:
                    param = pourcent_dec_get(url[1])
                params = extraire(param)

                # ordre de traitement : js intégré, tictac, touches, api, init, fichier
                if comm == chemin_js:
                    contenu = bytes(interlocuteur_js(), 'utf-8')
                    paquet = empaqueter(contenu, 'js')
                elif comm == '/__tictac':
                    if len(_battements) > int(params['ref']):
                        _battements[int(params['ref'])][0]()
                    contenu = bytes(json.dumps(_actions), 'utf-8')
                    _actions = {}
                    paquet = empaqueter(contenu, 'json')
                elif comm in _catalogue:
                    _catalogue[comm](comm, params)
                    contenu = bytes(json.dumps(_actions), 'utf-8')
                    _actions = {}
                    paquet = empaqueter(contenu, 'json')
                elif (
                    comm == '/__init'
                ):  # placé après le catalogue pour pouvoir court-circuiter
                    contenu = bytes(json.dumps(_actions), 'utf-8')
                    _actions = {}
                    paquet = empaqueter(contenu, 'json')
                else:  # on cherche le fichier
                    comm = '.' + comm
                    paquet = gen_fichier(
                        comm
                    )  # la fonction gen_fichier se charge de générer le 404 si elle ne trouve pas le fichier
                t.sendall(paquet)

            else:  # ce n'est pas une requête GET
                t.sendall(
                    bytes(
                        'HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain; charset=utf-8\r\nConnection: close\r\nContent-Length: 26\r\n\r\nRequête mal formée !\r\n\r\n',
                        'utf-8',
                    )
                )

        try:
            t.shutdown(socket.SHUT_WR)
            #            print ("Bye 1")
            t.close()
        #            print ("Bye 2")
        except:
            #            print('except shutdown')
            pass

    #    s.shutdown(socket.SHUT_RDWR)
    s.close()


def stop() -> None:
    """
    provoque l'arrêt du serveur après la fin du traitement de la requête en cours
    """
    global _continuer
    _continuer = False


def api(url: str, commande: callable) -> None:
    """
    Associe la commande à l'url.
    Actions effectuées par le serveur quand il reçoit une requête GET commande?param :
    - interpréter param comme le dictionnaire d
    - effectuer l'appel commande(url,d)
    - renvoyer en réponse à cette requête le contenu de _actions, au format json.
    """
    _catalogue[url] = commande


# def change_init(fnct : callable = lambda c,p : None) -> None:
#    """
#    À documenter
#    """
#    api("/__init", fnct)


def charge_page(page: str, comm_init: callable = None) -> None:
    """
    Programme la redirection de la page html affichée vers «page» au prochain appel d'une api.
    Facultatif : comm_init indique l'api à appeler au chargement de la page cible.
    """
    _actions['propage'] = page
    if not comm_init == None:
        api('/__init', comm_init)


def def_battement(tempo: int, commande: callable) -> int:
    """
    programme un appel de «commande» tous les «tempo» millisecondes via le javascript de la page
    les actions engagées par «commande» sont exécutées sur la page
    la valeur renvoyée est un identifiant du battement à utiliser pour le désactiver/le réactiver
    """
    if 'créer_batt' not in _actions:
        _actions['créer_batt'] = {}

    ref = len(_battements)

    _battements.append((commande, tempo))

    _actions['créer_batt'][str(ref)] = tempo

    return ref


def état_battement(ref: int, actif: bool) -> None:
    """
    active_désactive le battement «ref»
    """
    if actif:
        _actions['créer_batt'][str(ref)] = _battements[ref][1]
    else:
        if 'stop_batt' not in _actions:
            _actions['stop_batt'] = []
            _actions['stop_batt'].append(ref)


# def écouter_touches( activé : bool, comm : str, fnct : callable) -> None:
def écouter_touches(**kwargs) -> None:
    """
    écouter_touches( activé : bool, comm : str, fnct : callable = lambda c,p: None) -> None:
    écouter les touches du clavier
    """

    activé = kwargs['activé'] if 'activé' in kwargs else True
    comm = kwargs['comm'] if 'comm' in kwargs else ('/__ec.to__')
    fnct = kwargs['fnct'] if 'fnct' in kwargs else lambda c, p: None

    _actions['écouter_touches'] = activé and len(comm) > 0
    if activé and len(comm) > 0:
        _actions['comm_touches'] = comm
        api(comm, fnct)


def capture_clic(objet: str, **kwargs) -> None:
    """
    capture_clic(objet : str, activé : bool,  comm : str, fnct : callable = lambda c,p:None)
    définit l'événement onclick de l'objet
    """

    activé = kwargs['activé'] if 'activé' in kwargs else True
    comm = kwargs['comm'] if 'comm' in kwargs else ('/__cc__.' + objet)
    fnct = kwargs['fnct'] if 'fnct' in kwargs else lambda c, p: None

    if 'capture_clic' not in _actions:
        _actions['capture_clic'] = []

    _actions['capture_clic'].append([activé, objet, comm])

    if activé and len(comm) > 0:
        api(comm, fnct)


def classes(objet: str, classes: str) -> None:
    """
    Pour insérer dans le dictionnaire _actions les éléments permettant de fixer la classe de l'objet d'id «objet» à «valeur»
    """
    if not 'classes' in _actions:
        _actions['classes'] = {}
    _actions['classes'][objet] = classes


def lier_param(objet: str, paramètre: str) -> None:
    """
    Pour que la valeur de l'attribut «value» de l'objet d'id «objet» soit donnée au paramètre «paramètre» de chaque appel d'api (événements et tic-tacs inclus)
    """
    if not 'params' in _actions:
        _actions['params'] = {}
    _actions['params'][objet] = paramètre


def valeur(objet: str, value: str) -> None:
    """
    Pour insérer dans le dictionnaire _actions les éléments permettant de fixer l'attribut value de l'objet d'id «objet» à «value»
    """
    if not 'valeurs' in _actions:
        _actions['valeurs'] = {}
    _actions['valeurs'][objet] = value


def contenu(objet: str, contenu: str, alasuite=False) -> None:
    """
    Pour insérer dans le dictionnaire _actions les éléments permettant de fixer le contenu de l'objet d'id «objet» à «valeur»
    """
    if alasuite:
        motclé = 'alasuite'
        if not motclé in _actions:
            _actions[motclé] = {}
        if not objet in _actions[motclé]:
            _actions[motclé][objet] = []
        _actions[motclé][objet].append(contenu)
    else:
        motclé = 'contenu'
        if not motclé in _actions:
            _actions[motclé] = {}
        _actions[motclé][objet] = contenu


def init_page(fnct: callable = lambda c, p: None) -> None:
    """
    Définit une fonction d'initialisation pour chaque page, en remplacement de l'initialsation par défaut, qui purge les actions déjà engagées
    """
    api('/__init', fnct)


if __name__ == '__main__':
    # lance un serveur web de base
    # attention, il insère son script dans les pages .html
    servir()
