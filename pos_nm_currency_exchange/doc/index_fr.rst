=====================
Change de devises PdV
=====================

Un guichet de change dans le Point de Vente Odoo 20 : le client apporte des
billets dans une devise et repart avec des billets dans une autre, moins une
commission. Construit sur POS Multi-Currency Cash, qui contrôle le tiroir de
chaque devise, ses taux de caisse et ses pièces et billets.

Présentation
============

Les commerces des zones touristiques, les hôtels, les campings ou les villes
frontalières sont régulièrement sollicités pour changer de l'argent. Avec
POS Multi-Currency Cash, la caisse accepte déjà les billets étrangers et
peut rendre la monnaie dans une devise étrangère ; ce module ajoute
l'opération sans vente :

* le caissier ouvre l'entrée **Opération de change** du menu de la caisse,
  choisit la devise reçue et la devise rendue, et saisit le montant reçu,
  ou le montant que le client souhaite recevoir ;
* la caisse calcule l'opération : billets reçus au taux de caisse du point
  de vente (le taux d'achat), billets rendus au taux de vente du guichet,
  la commission de la devise, l'arrondi aux pièces et billets, et ce que
  contient le tiroir ;
* l'opération est enregistrée avec le caissier et, lorsque c'est requis, le
  client et sa pièce d'identité, et un ticket de change est imprimé ;
* les deux tiroirs bougent : les billets reçus entrent dans le tiroir de
  leur devise et les billets rendus sortent de l'autre, sur le journal
  d'espèces de la session, avec la commission comptabilisée sur un compte
  de produits dédié ;
* un administrateur du Point de Vente peut annuler une opération erronée
  tant que la session est ouverte et que le tiroir contient encore les
  billets reçus ;
* les opérations apparaissent dans le contrôle de clôture, dans le rapport
  *Position de change* et dans le rapport *Détails des ventes*, dans une
  liste avec un tableau croisé des commissions et des marges de taux, et
  dans un registre de change exportable ou imprimable pour une période ;
* le tableau des taux du guichet peut être affiché et imprimé à la caisse,
  ou imprimé en PDF ;
* plusieurs guichets d'un même établissement agréé peuvent former un
  **bureau de change** : ils partagent sa licence, ses règles
  d'identification et les mêmes taux, et le bureau affiche les tiroirs de
  chaque guichet ;
* au-delà de seuils que vous fixez, le client déclare l'origine des fonds,
  et l'opération est signalée *À examiner* pour le responsable
  conformité ;
* chaque opération est chaînée dans un registre inaltérable (chaîne de
  hachage), qui peut être vérifié et clôturé par période ;
* le tableau des taux peut être affiché en plein écran sur un écran tourné
  vers les clients, ou sur l'écran client d'Odoo, et recharge les taux de
  lui-même ;
* les pièces et billets étrangers reçus et rendus peuvent être comptés par
  coupure, avec le stock de chaque tiroir, et des billets peuvent être
  envoyés d'un guichet d'un bureau à un autre.

Tout ceci est facultatif : un guichet seul, sans bureau de change,
fonctionne comme avant.

Prérequis
=========

* L'application **Point de Vente** (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) **20.0.2.1.0 ou
  plus récent**, inclus dans le prix affiché sur l'Odoo Apps Store : 178 EUR
  au total, 59 EUR pour ce module plus 119 EUR pour POS Multi-Currency Cash
  (vous l'avez déjà acheté ? Contactez-nous à odoo@natimai.solutions avant
  d'acheter ce module), avec au moins une
  devise étrangère sur le mode de paiement espèces du point de vente (voir
  son guide : *Accepter une devise en espèces*). Une version plus
  ancienne de POS Multi-Currency
  Cash ne fonctionne pas avec ce module : mettez-la à jour d'abord. Avec
  la 20.0.2.1.1 ou plus récente, l'ouverture du bloc Espèces de la devise
  principale dans la fenêtre de clôture est affichée correctement quand la
  session a des opérations de change (avant, ce n'était qu'une erreur
  d'affichage : les montants comptés et comptabilisés étaient justes).
* Un **compte de produits pour les commissions** (type *Revenus* ou
  *Autres produits*).
* Pour transférer des billets entre les guichets d'un bureau de change :
  un **compte de fonds en transit** (type *Actifs circulants*).

Configuration
=============

Activer le guichet
------------------

Allez dans *Point de Vente → Configuration → Paramètres*, sélectionnez
votre point de vente et repérez la section **Opération de change** :

* **Opération de change** (activée par défaut) : affiche les entrées du
  guichet dans le menu de la caisse.
* **Compte de commission** : compte de produits qui reçoit les
  commissions. Seuls les comptes de produits peuvent être choisis. Il est
  requis pour enregistrer une opération.
* **Numéro de licence de change** : numéro de licence ou d'enregistrement
  de votre activité de change, imprimé sur les tickets et le tableau des
  taux lorsqu'il est renseigné.
* **Bureau de change** : le bureau de change de ce guichet (voir *Bureau
  de change et guichets*). Avec un bureau, la licence et les seuils
  d'identification ci-dessous sont masqués : ceux du bureau s'appliquent.
* **Client obligatoire au-delà de** : valeur d'une opération, dans la
  devise du point de vente, au-delà de laquelle le client doit être
  identifié.
* **Client obligatoire pour chaque opération** : chaque opération nomme
  son client.
* **Pièce d'identité obligatoire au-delà de** : valeur au-delà de laquelle
  la pièce d'identité du client est enregistrée sur l'opération.
* **Période des opérations liées (jours)** : lorsqu'elle est supérieure à
  0, la valeur comparée aux seuils est l'opération plus les opérations
  du même client sur ce nombre de jours (voir *Identification du client*).
* **Origine des fonds obligatoire au-delà de** : valeur au-delà de
  laquelle le client déclare l'origine des fonds (voir *Seuils de
  conformité*).
* **Examen au-delà de** : valeur au-delà de laquelle l'opération est
  signalée *À examiner* pour le responsable conformité. Elle n'est jamais
  refusée.
* **Suivre les billets par coupure** : les billets étrangers reçus et
  rendus sont comptés par pièce et billet (voir *Billets par coupure*).
* **Tableau des taux sur l'écran client** : l'écran client d'Odoo affiche
  le tableau des taux tant qu'aucune commande n'est en cours.
* **Adresse du tableau des taux** : adresse du tableau des taux en plein
  écran de ce guichet, pour un écran tourné vers les clients (voir
  *Tableau des taux sur un écran*).
* **Imprimer les taux de change** : imprime le tableau des taux du point de
  vente en PDF.

Les seuils à 0 ne sont jamais appliqués.

Commissions et marge de vente par devise
----------------------------------------

Allez dans *Point de Vente → Configuration → Devises en espèces* et
ouvrez la ligne de la devise. Le groupe *Opération de change* contient
quatre valeurs, les montants étant dans la devise du point de vente :

* **Marge de vente de change (%)** : marge du guichet sur les billets de
  cette devise qu'il rend (voir *Taux* ci-dessous). Masquée avec un taux de
  caisse fixe, où elle n'est pas utilisée. Une nouvelle devise part de sa
  Marge du taux de caisse (une marge négative devient la marge de vente qui
  garde le même taux de vente, comme à la mise à jour) ;
* **Commission de change (%)** : pourcentage de la valeur des billets
  reçus ;
* **Commission de change fixe** : partie fixe ajoutée au pourcentage ;
* **Commission de change minimale** : la commission est au moins ce
  montant.

La commission d'une opération est celle de la devise étrangère concernée
(la devise rendue lorsque les deux sont étrangères). Chaque modification
de ces valeurs est consignée dans le chatter de la ligne, comme les taux.

Taux
----

Le guichet achète à un taux et vend à un autre, toujours en faveur du
commerce. Les taux sont exprimés en unités de la devise étrangère pour une
unité de la devise du point de vente, comme dans POS Multi-Currency Cash :

* **Billets reçus** (taux d'achat) : le taux de caisse de POS
  Multi-Currency Cash, c'est-à-dire le taux d'Odoo avec la **Marge du taux
  de caisse (%)** de la devise, ou son **Taux fixe**.
* **Billets rendus** (taux de vente) : le taux d'Odoo divisé par 1 + la
  **Marge de vente de change**. Avec un taux de caisse fixe, le plus bas
  du **Taux fixe** et du **Taux fixe de la monnaie** (un Taux fixe de la
  monnaie à 0 vaut le Taux fixe) : le taux le plus bas rend moins de
  billets.

Exemple, point de vente en USD, taux d'Odoo de 2 EUR pour 1 USD, Marge du
taux de caisse et Marge de vente de change de 10 % : le guichet achète les
euros à 2 × 1,10 = 2,20 EUR pour 1 USD (100 EUR reçus valent 45,45 $) et
les vend à 2 / 1,10 = 1,8182 EUR pour 1 USD (100 EUR rendus valent
55,00 $), avant la commission.

L'écart avec les taux d'Odoo est la **Marge de taux** de l'opération (voir
*Notes comptables*). Lors d'une mise à jour depuis 20.0.1.x, la Marge de vente de change de chaque devise prend la valeur
de sa Marge du taux de caisse : vérifiez-la.

Pièces et billets
-----------------

Les billets rendus sont arrondis une fois, *à la baisse*, à la plus petite
pièce ou au plus petit billet de leur devise, de sorte que le caissier
n'ait jamais à rendre des pièces qui n'existent pas dans le tiroir ; le
reste demeure dans la commission, qui n'est jamais inférieure à celle
configurée :

* une devise étrangère : son **Arrondi de la monnaie**, sinon l'arrondi de
  la devise ;
* la devise du point de vente : la méthode d'arrondi de l'**Arrondi du
  total** dans les paramètres du point de vente, lorsqu'il est activé,
  sinon l'arrondi de la devise.

Ticket
------

Le ticket de change imprime le logo, l'**en-tête** et le **pied de page**
du point de vente (*Paramètres*, section *Factures & Reçus*, *En-tête &
pied de page personnalisés*), le numéro de licence de change et les
coordonnées de la société. Indiquez-y les mentions légales que votre
activité doit présenter au client. Avec les billets comptés par coupure,
le ticket liste les billets sous les montants.

Bureau de change et guichets
----------------------------

Un bureau de change est un établissement agréé avec un ou plusieurs
guichets (points de vente). Il est facultatif : un guichet hors de tout
bureau garde ses propres paramètres.

Allez dans *Point de Vente → Configuration → Bureaux de change* et
appuyez sur **Nouveau**. Donnez un nom au bureau, puis renseignez :

* groupe *Bureau* : l'**Adresse** (imprimée sur le registre de change et
  le tableau des taux), le **Numéro de licence de change**, le
  **Responsable conformité** (il reçoit une activité pour chaque opération
  signalée *À examiner*) et le **Compte de fonds en transit** (voir
  *Compte de fonds en transit*) ;
* groupe *Identification* : **Client obligatoire pour chaque opération**,
  **Client obligatoire au-delà de**, **Pièce d'identité obligatoire
  au-delà de**, **Origine des fonds obligatoire au-delà de**, **Examen
  au-delà de** et **Période des opérations liées** (jours). Ils
  fonctionnent comme les paramètres du même nom d'un point de vente, dans
  la devise de la société.

La licence et les règles du bureau remplacent celles de ses guichets. Pour
ajouter un guichet, renseignez son **Bureau de change** dans la section
*Opération de change* des paramètres du point de vente, ou ajoutez-le dans
l'onglet **Guichets** du bureau. Les guichets d'un bureau doivent utiliser
la devise de sa société.

Les boutons intelligents du bureau ouvrent ses **Guichets**, ses
**Opérations** et ses **Transferts** de billets.

Les mêmes taux à chaque guichet
-------------------------------

Dans l'onglet **Guichets** du bureau, choisissez le **Guichet de
référence** : le guichet dont les autres copient les taux, et dont le
tableau des taux du bureau affiche les taux. Puis, avec deux guichets ou
plus :

* **Appliquer les taux aux guichets** copie aux autres guichets, pour
  chaque devise du guichet de référence, le taux de caisse (mode de taux,
  marge, taux fixes), les arrondis des pièces et billets, la **Marge de
  vente de change (%)** et les commissions. Les modifications du taux de
  caisse, de la marge de vente et des commissions sont consignées dans le
  chatter de la devise (pas celles des arrondis). Un guichet qui ne prend pas la
  devise en espèces est ignoré et nommé dans un avertissement ;
* **Écarts de taux** liste ce qui diffère encore du guichet de référence.

Appliquez à nouveau les taux après chaque modification du guichet de
référence.

Seuils de conformité
--------------------

Deux seuils vous aident à appliquer les règles de lutte contre le
blanchiment de votre pays. Ils se règlent sur le bureau de change, ou dans
les paramètres d'un point de vente hors de tout bureau, dans la devise du
point de vente ; à 0, ils ne sont jamais appliqués. Les opérations liées du
client comptent, comme pour les autres seuils.

* **Origine des fonds obligatoire au-delà de** : l'opération exige un
  client, et le client déclare l'origine des fonds. *Autre* exige des
  précisions.
* **Examen au-delà de** : l'opération est signalée *À examiner*. Elle
  n'est jamais refusée au guichet. Une activité est envoyée au
  **Responsable conformité** du bureau.

Une opération dont le client déclare être une personne politiquement
exposée est aussi signalée *À examiner*. Choisissez un administrateur du
Point de Vente comme responsable conformité : seuls les administrateurs du
Point de Vente peuvent examiner les opérations.

Tableau des taux sur un écran
-----------------------------

Chaque guichet a une page publique du tableau des taux pour une
télévision, une tablette ou tout écran tourné vers les clients. Son
adresse est l'**Adresse du tableau des taux** dans la section *Opération
de change* des paramètres du point de vente. Elle contient le jeton
d'accès du point de vente, celui de son écran client : ne la partagez
qu'avec les écrans du guichet.

Un bureau de change a sa propre page, dans l'onglet **Tableau des taux**
du bureau (administrateurs du Point de Vente) : l'**Adresse du tableau des
taux** affiche les taux du guichet de référence sous le nom, l'adresse et
la licence du bureau. **Rafraîchissement du tableau (secondes)** règle la
fréquence à laquelle la page recharge les taux (60 par défaut, 10 au
moins), aussi pour les pages de ses guichets. **Nouvelle adresse** donne
une nouvelle adresse à la page du bureau : les écrans qui affichent
l'ancienne ne reçoivent plus les taux (ils gardent les derniers taux avec
« Connexion perdue : derniers taux affichés », puis n'affichent plus rien une fois
la page rechargée).

Pour afficher le tableau sur l'écran client d'Odoo, cochez **Tableau des
taux sur l'écran client** dans les paramètres du point de vente.

Billets par coupure
-------------------

POS Multi-Currency Cash compte déjà les pièces et billets de chaque devise
étrangère à l'ouverture et à la clôture. Ce module peut aussi les suivre
pendant la session :

1. Allez dans *Point de Vente → Configuration → Pièces/billets* et
   vérifiez que les pièces et billets de chaque devise étrangère existent,
   avec leur **Devise** renseignée (voir le guide de POS Multi-Currency
   Cash).
2. Dans les paramètres du point de vente, cochez **Suivre les billets par
   coupure**.

L'option s'applique aux devises étrangères en espèces qui ont des pièces et
billets sur ce point de vente. La devise du point de vente n'est pas
suivie : elle n'a pas de comptage par coupure. Comptez l'ouverture par
pièces et billets, pour que le stock du tiroir parte juste.

Compte de fonds en transit
--------------------------

Les billets envoyés d'un guichet d'un bureau à un autre passent par le
**Compte de fonds en transit** du bureau : un compte d'actifs circulants
(type *Actifs circulants*). Créez-en un dans votre plan comptable si
besoin, par exemple « Billets en transit », et renseignez-le sur le
bureau. Son solde est la valeur des billets envoyés et pas encore reçus.
Sans lui, les billets ne peuvent pas être transférés.

Qui peut faire quoi
-------------------

* Les **utilisateurs du Point de Vente** (caissiers) enregistrent les
  opérations à la caisse, réimpriment leurs tickets et affichent le tableau
  des taux. Ils peuvent lire les opérations mais pas les modifier.
* Les **administrateurs du Point de Vente** (accès *Point de Vente* :
  *Administrateur*) voient en plus les menus *Point de Vente → Commandes
  → Opérations de change* et *Point de Vente → Analyse → Registre de
  change* et les pièces d'identité des clients, peuvent modifier la note
  d'une opération et annuler une opération.
* Dans un bureau avec un autre guichet activé, les utilisateurs du Point
  de Vente envoient et reçoivent aussi des billets à la caisse (*Envoyer
  des billets*, *Recevoir des billets*), et voient le *Stock de billets*
  de leur tiroir lorsque les billets sont suivis.
* Les administrateurs du Point de Vente gèrent aussi les bureaux de change
  (*Point de Vente → Configuration → Bureaux de change*, avec les onglets
  **Tiroirs** et **Tableau des taux**), les transferts de billets (*Point
  de Vente → Commandes → Transferts de billets*), et voient *Point de
  Vente → Analyse → Stock de billets*, *Mouvements de billets* et
  *Clôtures du registre de change*.
* Seuls les administrateurs du Point de Vente voient les déclarations du
  client et examinent les opérations (**Conformité**, **Note de
  conformité**), vérifient l'intégrité du registre et le clôturent.
* Personne ne peut supprimer une opération ni l'une de ses lignes de
  relevé, un mouvement de billets, une clôture du registre ni un transfert
  de billets une fois envoyé.
* Avec plusieurs sociétés, chaque utilisateur voit les opérations des
  sociétés auxquelles il a accès.
* Avec le module Employés (``pos_hr``), le caissier d'une opération est
  l'employé connecté à la caisse, qui doit être autorisé sur le point de
  vente ; sinon c'est l'utilisateur.

Travail quotidien
=================

Échanger des devises
--------------------

Depuis n'importe quel écran de la caisse, ouvrez le menu (en haut à
droite) et appuyez sur **Opération de change** :

1. choisissez la devise **reçue du client** et saisissez le montant ;
2. choisissez la devise **rendue au client**. Le montant rendu, le taux,
   la valeur des billets reçus, la commission et le solde du tiroir
   (**Dans le tiroir**) sont calculés au fur et à mesure de la saisie. Le
   bouton flèche échange les deux devises ;
3. lorsque le client demande un montant exact, saisissez-le plutôt dans le
   champ **Rendu au client** : le montant à recevoir est calculé, arrondi
   à la hausse aux pièces de la devise reçue, et l'indication « Montant à
   recevoir calculé à partir du montant rendu. » s'affiche. En quittant le
   champ, il affiche le montant réellement rendu, qui peut être légèrement
   supérieur lorsque les billets ne permettent pas de faire le montant
   exact. Saisir à nouveau dans **Reçu du client** revient au calcul
   normal ;
4. lorsque le client doit être identifié, le bouton **Client** devient
   rouge avec la raison : appuyez dessus et choisissez le client (créez-le
   si besoin). Lorsque la pièce d'identité est requise, ses champs
   apparaissent : type, pays de délivrance et date d'expiration sont
   préremplis depuis le contact, et le champ du numéro n'affiche, en
   indication, que les 4 derniers caractères du numéro enregistré. Type,
   numéro et date d'expiration sont obligatoires ; pour une pièce sans
   date d'expiration (une ancienne carte d'identité), cochez **Sans date
   d'expiration** à la place. **Nationalité** et
   **Date de naissance** s'affichent vides : laissés vides, ils gardent
   les valeurs du contact. Pour la même pièce (même type, numéro laissé
   vide), le numéro et les autres champs laissés vides gardent aussi les
   valeurs du contact ; pour une autre pièce, saisissez son numéro ;
5. ajoutez une note si utile, puis **Confirmer**. Le tiroir-caisse
   s'ouvre, le ticket de change s'imprime et une notification résume
   l'opération.

**Confirmer** reste désactivé pendant un calcul, et lorsque le tiroir de
la devise rendue ne contient pas le montant (la ligne *Dans le tiroir* est
alors rouge, avec le refus).

Si la connexion est perdue pendant la confirmation, la fenêtre indique que
l'opération a peut-être été enregistrée : confirmez à nouveau une fois la
connexion rétablie. D'ici là, montants, devises, client, pièce et note ne
peuvent plus être modifiés. Une opération déjà enregistrée ne l'est pas
deux fois, et son ticket est imprimé. Si la connexion est perdue pendant le
calcul de la cotation, la fenêtre l'indique et redemande la cotation
quelques secondes plus tard.

Lorsque le guichet ne peut pas fonctionner sur ce point de vente, l'entrée
**Opération de change** affiche la raison au lieu de la fenêtre : aucune
devise étrangère sur le mode de paiement espèces, ou aucun compte de
commission.

Déclarations du client
----------------------

Au-delà du seuil **Origine des fonds obligatoire au-delà de** ou du seuil
**Examen au-delà de**, une fois le client choisi, la fenêtre affiche
**Déclarations du client** :

* **Origine des fonds** : Salaire ou pension, Épargne, Revenus
  professionnels, Vente d'un bien, Héritage ou donation, Autre.
  Obligatoire au-delà du seuil d'origine des fonds ; pour *Autre*,
  saisissez les **Précisions sur l'origine des fonds** ;
* **Objet de l'opération** : Voyage, Activité professionnelle, Études,
  Soutien familial, Autre ;
* **Personne politiquement exposée (PPE), ou membre de sa famille ou
  personne étroitement associée** : cochez cette case lorsque le client
  le déclare. L'opération est alors signalée *À examiner*.

Au-delà du seul seuil d'examen, les déclarations sont demandées mais pas
obligatoires. Elles sont figées sur l'opération avec l'adresse du client.
Le caissier n'est jamais bloqué par un examen : le responsable conformité
vérifie l'opération plus tard (voir *À examiner*).

Compter les billets
-------------------

Avec **Suivre les billets par coupure**, la fenêtre s'élargit et affiche
une grille pour chaque devise étrangère suivie de l'opération :

* **Billets reçus** : saisissez la **Quantité** de chaque pièce et billet
  que donne le client. Le **Total** doit être égal au montant reçu ;
* **Billets rendus** : les quantités sont proposées depuis le stock du
  tiroir, les plus gros billets d'abord. **Dans le tiroir** donne le stock
  de chaque pièce et billet. Modifiez les quantités si vous rendez
  d'autres billets : le **Total** doit être égal au montant rendu.

Un message rouge s'affiche lorsqu'un total ne correspond pas, et
**Confirmer** reste désactivé. Lorsque le tiroir manque de certains
billets, un message orange les nomme : « Il manque ... dans le tiroir :
vérifiez les billets avant de les rendre. » Ce n'est qu'un avertissement,
car les ventes en espèces dans une devise étrangère font bouger le tiroir
sans coupures : le stock peut être en retard sur le tiroir réel. Lorsque
le montant rendu ne peut pas être composé avec les pièces et billets de la
devise, la fenêtre l'affiche comme une erreur.

Stock de billets
----------------

L'entrée **Stock de billets** du menu de la caisse (affichée lorsque les
billets sont suivis) donne, pour chaque devise suivie et chaque pièce et
billet, le comptage d'**Ouverture**, les billets déplacés par les
**Opérations de change** et les transferts, et le stock **Dans le
tiroir**. Lorsque l'ouverture n'a pas été comptée par pièces et billets,
la fenêtre l'indique : le stock ne compte alors que les opérations de
change.

À la clôture, la fenêtre de comptage de chaque devise suivie affiche, à
côté du comptage, la quantité attendue de chaque pièce et billet
(*attendu*), lorsque l'ouverture a été comptée par pièces et billets ou
que le tiroir était vide à l'ouverture.

Envoyer et recevoir des billets
-------------------------------

Un guichet d'un bureau de change avec un autre guichet activé a deux
entrées de plus dans le menu de la caisse.

**Envoyer des billets** :

1. choisissez le guichet dans **Envoyer à**. Lorsqu'aucune caisse n'y est
   ouverte, la fenêtre avertit que les billets restent en transit jusqu'à
   leur réception ;
2. choisissez la devise et saisissez le **Montant envoyé**. Avec les
   billets suivis, la grille **Billets envoyés** propose les billets du
   stock du tiroir ; leur **Total** doit être égal au montant ;
3. ajoutez une note si utile, puis **Confirmer**. Le tiroir-caisse
   s'ouvre et un bordereau de transfert s'imprime : joignez-le aux
   billets.

Le tiroir doit contenir le montant. Le transfert reçoit sa référence
(``TRF/AAAA/NNNNN``) et les billets quittent le tiroir : une sortie
d'espèces sur la session, sur le compte de fonds en transit du bureau.

**Recevoir des billets** liste les billets en transit vers ce guichet :
référence, date d'envoi, guichet expéditeur, montant et billets. Comptez
les billets, puis appuyez sur **Recevoir** : les billets entrent dans le
tiroir (une entrée d'espèces de même valeur) et un bordereau s'imprime.
Lorsque le guichet expéditeur n'a pas compté les billets par coupure et
que ce guichet les suit, **Recevoir** ouvre la grille **Billets reçus**,
préremplie avec les plus gros billets d'abord : corrigez-la selon les
billets réellement reçus, puis appuyez sur **Confirmer la réception**.
**Actualiser** recharge la liste.

Le montant reçu est le montant envoyé. Un écart apparaît dans le comptage
de clôture du tiroir qui reçoit.

Le tableau des taux sur un écran
--------------------------------

Ouvrez l'**Adresse du tableau des taux** du guichet, ou celle du bureau
(bouton **Ouvrir le tableau des taux** du bureau), dans le navigateur de
l'écran et passez-le en plein écran. La page affiche les devises avec
**Nous achetons**, **Nous vendons**, **Vous recevez pour** et **Vous payez
pour** le montant
type, la commission de chaque devise, la licence, la date et l'heure. Elle
recharge les taux d'elle-même. Lorsque la connexion est perdue, elle garde
les derniers taux à l'écran avec le message « Connexion perdue : derniers
taux affichés ».

Le tableau s'affiche dans la langue de la société (celle de son contact).
Pour une autre langue installée dans la base, ajoutez-la à l'adresse :
``&lang=fr_FR`` pour le français, ``&lang=en_US`` pour l'anglais, etc.

Avec **Tableau des taux sur l'écran client**, l'écran client d'Odoo
affiche le tableau du guichet tant qu'aucune commande n'est en cours.

L'avertissement sur les pièces
------------------------------

Un avertissement orange apparaît lorsque le montant reçu dans une devise
étrangère ne peut pas être composé avec ses pièces et billets, par exemple
1 106 XPF avec des pièces de 5 XPF. Le pas vérifié est l'**Arrondi des
paiements** de la devise, sinon son **Arrondi de la monnaie** lorsque son
**Reste de la monnaie** est *Gardé comme arrondi*. L'avertissement ne
bloque pas l'opération : vérifiez les billets réellement reçus et corrigez
le montant si besoin.

Refus
-----

La caisse refuse une opération, avec un message, lorsque :

* le tiroir de la devise rendue ne contient pas le montant, devise du
  point de vente comprise (le solde est celui du contrôle de clôture :
  ouverture, ventes en espèces et monnaie rendue, mouvements d'espèces et
  opérations de change de la session) ;
* le montant est trop faible : une fois la commission déduite, aucun
  billet ne peut être rendu ;
* la même devise est choisie des deux côtés ;
* le client, ou une pièce d'identité valide, est requis et manquant, ou la
  pièce a expiré ;
* l'origine des fonds est requise et n'est pas déclarée ;
* avec les billets suivis, les billets reçus ou rendus ne correspondent
  pas aux montants ;
* la cotation a changé entre la fenêtre et le serveur (taux, marge ou
  commission modifiés entre-temps) : rien n'est enregistré, la fenêtre
  affiche aussitôt la nouvelle cotation avec un avertissement ; vérifiez-la
  avec le client, puis confirmez à nouveau ;
* la session n'est pas ouverte, ou le guichet est désactivé.

Réimprimer un ticket
--------------------

L'entrée **Opérations de change** du menu de la caisse liste les
opérations de la session (référence, date, opération, reçu, rendu,
client). **Réimprimer** imprime à nouveau le ticket, marqué *COPIE* ; une
opération annulée depuis est marquée *ANNULÉ* avec la date et l'heure.

Afficher les taux
-----------------

L'entrée **Taux de change** du menu de la caisse affiche le tableau des
taux du guichet, une ligne par devise étrangère en espèces :

* **Nous achetons** : valeur de 1 unité des billets reçus (taux de caisse,
  avant la commission), et **Vous recevez** : ce que le client reçoit pour
  un montant type, commission déduite et arrondi aux billets ;
* **Nous vendons** : prix de 1 unité des billets rendus (taux de vente,
  avant la commission), et **Vous payez** : ce que le client paie pour un
  montant type, commission incluse ;
* **Commission** : pourcentage, part fixe et minimum.

Le montant type est la puissance de 10 la plus proche de 100 unités de la
devise du point de vente (100 EUR, 10 000 XPF, 1 000 000 VND), arrondie
aux pièces que le guichet prend et rend dans cette devise (son Arrondi des
paiements et son Arrondi de la monnaie : 99 CHF avec des pièces de 3 CHF). Les montants
sont calculés par la cotation du guichet : ils correspondent aux
opérations. **Imprimer** imprime le tableau sur l'imprimante de tickets.

Annuler une opération
---------------------

Une opération erronée s'annule, elle ne se corrige pas par une autre
opération : une opération inverse prélèverait à nouveau la commission et
arrondirait à nouveau les billets, et un mouvement d'espèces laisserait la
commission sur le compte de commission.

Un administrateur du Point de Vente ouvre l'opération (*Point de Vente →
Commandes → Opérations de change*), appuie sur **Annuler l'opération**,
puis confirme. C'est possible tant que la session de l'opération est
ouverte et que le tiroir contient encore les billets reçus (le client les
récupère). Deux lignes de relevé exactement opposées aux lignes d'origine
sont comptabilisées sur la session : mêmes montants dans les deux devises,
même compte de contrepartie. Les deux tiroirs et le compte de commission
reviennent à leur état d'avant l'opération.

L'opération passe à **Annulée**, avec la date et l'utilisateur, un message
est publié sur la session et sur l'opération, et elle ne compte plus dans
les commissions, le résumé de clôture et les rapports. Son ticket,
réimprimé, est marqué *ANNULÉ*. Avec les billets suivis, le stock du
tiroir est rétabli : les billets reçus en sortent et les billets rendus y
reviennent (mouvements de billets *Annulation*). L'annulation reçoit son propre
hachage dans le registre (**Hachage de l'annulation**), et une opération
d'une période du registre clôturée ne peut pas être annulée.

Une fois la session clôturée, une opération ne peut plus être annulée.
Corrigez-la alors par une opération inverse (la commission et l'arrondi
s'appliquent à nouveau ; mettez la commission de la devise à 0 le temps de
l'opération si vous la remboursez) ou par des mouvements d'espèces de
chaque devise, et demandez à votre comptable de reprendre la commission
sur le compte de commission.

Clôture de la session
---------------------

La fenêtre de clôture affiche un bloc **Opération de change** dès que la
session a des opérations : le nombre d'opérations, chaque opération (reçu,
rendu, caissier), le total des commissions, la **Marge de taux** et le
nombre d'opérations annulées. Les billets reçus et rendus sont déjà
compris dans les montants attendus de leurs devises : un change est une
entrée d'espèces sur un tiroir et une sortie sur l'autre, toutes deux
listées dans les mouvements de la devise.

Identification du client
========================

Les seuils vous aident à appliquer les règles d'identification de votre
pays ; le module enregistre ce que saisit le caissier, il ne vérifie pas
les pièces d'identité auprès d'un quelconque registre.

* La valeur comparée aux seuils est la valeur des billets reçus, dans la
  devise du point de vente.
* Avec une **Période des opérations liées**, les opérations effectuées (non
  annulées) par le même client sur les derniers jours, à tous les points
  de vente de la société, sont ajoutées, converties dans la devise du point
  de vente. Lorsque ce total dépasse un seuil, la fenêtre affiche « Avec
  les opérations liées du client » et le total ; sinon les autres
  opérations du client ne sont pas montrées. Sans client, seule l'opération compte : activez
  **Client obligatoire pour chaque opération** pour que la règle
  s'applique toujours.
* Au-delà de **Client obligatoire au-delà de**, l'opération exige un
  client.
* Au-delà de **Pièce d'identité obligatoire au-delà de**, elle exige un
  client et une pièce d'identité valide : type (Passeport, Carte
  d'identité, Permis de conduire, Titre de séjour, Autre), numéro, pays de
  délivrance, date d'expiration (ou **Sans date d'expiration** pour une
  pièce qui n'en a pas), nationalité et date de naissance. Une pièce
  expirée est refusée.

Le serveur vérifie à nouveau ces règles lors de l'enregistrement. La pièce
saisie à la caisse, lorsqu'elle diffère de celle enregistrée, est
enregistrée sur le contact (onglet **Pièce d'identité** de la fiche
contact) et une copie est conservée sur
l'opération avec le nom du client : modifier ou renommer le contact
ensuite ne change pas les opérations enregistrées. Le ticket imprime le nom
du client et le type de pièce avec seulement les 4 derniers caractères de
son numéro (par exemple « Passeport \*\*\*\*4567 »).

Les pièces d'identité ne sont visibles que des administrateurs du Point de
Vente ; dans la fenêtre, le caissier voit le type, le pays d'émission, la
date d'expiration et les 4 derniers caractères du numéro du client
sélectionné. Une pièce modifiée à la caisse est tracée sur le contact. Le
contact d'un utilisateur interne, même archivé, n'est modifié que par un
administrateur du Point de Vente (la pièce reste alors sur l'opération) ;
un client disposant d'un compte portail est un client comme un autre.

Consulter les opérations
========================

Opérations de change
--------------------

*Point de Vente → Commandes → Opérations de change* (administrateurs du
Point de Vente) liste les opérations avec leur référence, leur date, le
point de vente, le caissier, le client, les billets reçus et rendus, la
commission, la marge de taux et le statut. La liste s'ouvre avec le filtre
**Effectuée** ; le filtre **Annulée** affiche les opérations annulées.
Autres filtres : *Aujourd'hui*, *Avec client*, *Achat de devises*, *Vente
de devises*, *Change croisé* ; regroupement par point de vente, session,
caissier, type d'opération, statut, devise ou date. Le tableau croisé
donne les commissions, marges de taux et valeurs reçues par jour, statut
et devise reçue ; regroupez-le par point de vente, session ou caissier au
besoin.

Le type d'opération est vu du commerce : *Achat de devises* lorsqu'il
reçoit des billets étrangers, *Vente de devises* lorsqu'il rend des
billets étrangers, *Change croisé* entre deux devises étrangères.

La fiche d'une opération affiche ses montants, le **Taux appliqué**
(« 1 USD = 119,33 XPF »), la commission, la marge de taux, la pièce
d'identité et le chatter. Ses boutons :

* **Envoyer par e-mail** (lorsque l'opération a un client) : envoie le
  ticket en PDF avec le modèle *Opération de change : envoi du ticket* ;
* **Imprimer** : le ticket en PDF (*Ticket de change*) ;
* **Annuler l'opération** (voir plus haut) ;
* **Lignes de relevé** : les deux lignes de l'opération, et les deux
  lignes de son annulation.

Seules la **Note**, la **Conformité** et la **Note de conformité**
peuvent être modifiées, par un administrateur du Point de Vente (voir
*À examiner*) ; les modifications de la **Note** et de la **Conformité**
sont consignées dans le chatter.

La fiche de session dispose d'un bouton avec le total des commissions et
« Opérations : N », le nombre d'opérations effectuées ; il les ouvre.

Dans un bureau de change, l'opération affiche aussi son **Bureau de
change** et sa **Licence**, et la liste peut être regroupée par **Bureau
de change**. Avec les billets suivis, le bouton **Mouvements de billets**
ouvre les pièces et billets de l'opération.

À examiner
----------

Le filtre **À examiner** des *Opérations de change* donne les opérations
signalées au responsable conformité : au-delà du seuil d'examen, ou avec
une personne politiquement exposée déclarée. Le responsable conformité du
bureau reçoit aussi une activité « Examiner l'opération de change ... ».

Le groupe **Déclarations et conformité** de l'opération (administrateurs
du Point de Vente) affiche l'**Origine des fonds**, les **Précisions sur
l'origine des fonds**, l'**Objet**, **Personne politiquement exposée
(PPE)**, le **Motif de l'examen**, et les deux champs de l'examen :

* **Conformité** : Aucune, À examiner, Examinée ou Déclarée. Choisissez
  *Examinée* une fois l'opération vérifiée, ou *Déclarée* lorsque vous
  avez déclaré l'opération aux autorités ;
* **Note de conformité** : ce que vous avez vérifié ou décidé.

Ces deux champs et la **Note** sont les seuls qu'un administrateur du
Point de Vente peut modifier ; les modifications de **Conformité** et de
la **Note** sont consignées dans le chatter. Le groupe **Pièce
d'identité** affiche désormais aussi l'**Adresse du client** de
l'opération.

Détails des ventes
------------------

Le rapport *Détails des ventes* se termine par un tableau *Opération de
change* : chaque opération avec sa session, ses montants, sa commission et
sa marge de taux, puis les totaux, une ligne par devise des points de
vente, et la liste des opérations annulées, qui ne sont pas comptées.
Imprimé depuis une session, il couvre les opérations de la session ; lancé
depuis *Point de Vente → Analyse → Détails des ventes* pour une période,
il couvre les opérations datées de cette période sur les points de vente
sélectionnés (tous lorsqu'aucun n'est sélectionné), sessions ouvertes
comprises. Le rapport *Position de change* de POS Multi-Currency Cash
reflète les billets déplacés.

Registre de change
------------------

*Point de Vente → Analyse → Registre de change* (administrateurs du
Point de Vente) liste chaque opération dans l'ordre de sa référence, y
compris les opérations annulées (grisées, avec leur statut), avec le
caissier, le type d'opération, les montants, le taux, la commission, la
marge de taux, le nom du client et la pièce d'identité. Les références se
suivent sans trou. Exportez-le vers Excel avec l'action standard
*Exporter*.

**Imprimer le registre** demande une période (**Du**, **Au**, par défaut
du début du mois à maintenant) et les **Points de vente** (tous lorsque
vide), et imprime le registre en PDF (A4 paysage) avec les totaux par
devise : nombre d'opérations, reçu, rendu, solde, commissions et marges de
taux. Les opérations annulées sont listées mais non comptées dans les
totaux.

La liste affiche aussi l'**Origine des fonds** et la **Conformité** de
chaque opération ; le **Bureau de change**, la **Licence**, l'**Adresse du
client**, l'**Objet**, **Personne politiquement exposée (PPE)** et le
**Hachage du registre** peuvent être ajoutés depuis les colonnes
optionnelles. Dans l'assistant, choisissez un **Bureau de change** pour
imprimer le registre de ses seuls guichets. Le PDF affiche alors le
bureau, son adresse et sa licence ; il donne aussi, pour chaque
opération, l'adresse, la nationalité et la date de naissance du client,
les déclarations, le statut de conformité et le hachage.

Intégrité du registre
---------------------

Chaque opération est hachée (SHA-256) lors de son enregistrement, avec le
hachage de l'opération précédente de la société : les opérations forment
une chaîne. Une annulation reçoit son propre hachage, chaîné au hachage de
l'opération. La fiche de l'opération les affiche dans le groupe
**Registre** : **Hachage du registre**, **Hachage précédent** et
**Hachage de l'annulation**. Odoo refuse toute modification des champs
couverts par le hachage d'une opération (montants, devises, client, pièce
d'identité, origine des fonds, PPE, hachages), même par l'administrateur ;
seules la **Note** et la revue de conformité restent modifiables.

Pour vérifier la chaîne, appuyez sur **Imprimer le registre**, puis sur
**Vérifier l'intégrité**. La vérification recalcule, dans l'ordre, les
hachages de chaque opération de la société :

* « N opérations vérifiées : le registre est intact (dernière : ...) »
  lorsque chaque hachage correspond. Les opérations sans hachage,
  enregistrées avant le début de la chaîne, sont comptées à part ;
* sinon « Échec de la vérification d'intégrité sur ... », avec la
  première opération qui ne correspond pas et la raison : hachage
  manquant, chaîne rompue, l'opération a été altérée, ou l'annulation a
  été altérée.

La chaîne de hachage montre qu'une opération a été modifiée ou supprimée
directement dans la base de données. Elle n'empêche pas une telle
modification, et elle ne peut pas montrer que les dernières opérations
ont été supprimées : comparez avec le **Hachage de la dernière opération**
de la dernière clôture du registre, ou avec un registre imprimé.

Clôtures du registre
--------------------

Clôturez le registre d'une période une fois celle-ci terminée, par exemple
chaque mois :

1. *Point de Vente → Analyse → Registre de change*, **Imprimer le
   registre** ;
2. renseignez **Du** et **Au**, et le **Bureau de change** pour clôturer
   le registre d'un bureau (laissez-le vide, sans point de vente, pour
   toute la société) ;
3. appuyez sur **Clôturer la période** et confirmez. La clôture est
   irréversible.

Le registre n'est clôturé que lorsque la période est terminée, que les
sessions de ses opérations sont clôturées, qu'il ne chevauche pas une
autre clôture du même bureau ou de toute la société (pour une clôture de
toute la société : aucune clôture d'un de ses bureaux non plus), et que la vérification
d'intégrité réussit. La clôture reçoit une référence sans trou
(``EXR/AAAA/NNNN``) et fige le nombre d'**Opérations** et d'opérations
annulées (**Annulée**), la **Première référence** et la **Dernière
référence**, les **Commissions**, les **Marges de taux**, le résultat de
la vérification (**Intégrité**) et le **Hachage de la dernière
opération**. Le registre PDF de la période est joint : **Télécharger le
registre**.

Les clôtures sont listées dans *Point de Vente → Analyse → Clôtures du
registre de change*. Elles ne peuvent être ni modifiées ni supprimées, et
une opération d'une période clôturée ne peut plus être annulée.

Stock de billets et mouvements de billets
-----------------------------------------

*Point de Vente → Analyse → Stock de billets* (administrateurs du Point de
Vente) donne, par session, devise et **Coupure**, le comptage
d'**Ouverture**, les pièces et billets entrés (**Entrées**) et sortis
(**Sorties**) par les opérations et les transferts, le **Stock**, le
comptage de **Clôture** et l'**Écart** (clôture moins stock, lorsque les
deux comptages ont été faits par pièces et billets). Un écart négatif est
en rouge, un écart positif en orange. Le filtre **Écarts** garde les
lignes qui ne correspondent pas ; un tableau croisé donne le stock par
devise et coupure.

*Point de Vente → Analyse → Mouvements de billets* liste chaque pièce et
billet déplacé : par une opération de change, une annulation ou un
transfert, avec sa session, son opération ou son transfert, la
**Coupure** et la **Quantité**. Les mouvements ne sont jamais modifiés ni
supprimés.

Transferts de billets
---------------------

*Point de Vente → Commandes → Transferts de billets* (administrateurs du
Point de Vente) liste les transferts avec leur référence, leur bureau, le
**Guichet expéditeur**, le **Guichet destinataire**, le montant, la
valeur, les dates et le statut : Brouillon, En transit, Reçu ou Transfert
annulé. Le filtre **En transit** donne les billets envoyés et pas encore
reçus.

Un administrateur du Point de Vente peut aussi faire un transfert depuis
le back-office : **Nouveau**, choisissez le bureau, les guichets, la
devise et le montant, puis **Envoyer**. Le guichet expéditeur doit avoir
une session ouverte. Lorsqu'il suit les billets, ce sont les billets
proposés depuis son stock qui sont envoyés ; si son stock ne permet pas de
composer exactement le montant, l'envoi est refusé (« Saisissez les
billets envoyés par coupure ») : envoyez alors depuis la caisse pour
choisir les billets. **Recevoir** met les billets dans le tiroir du guichet
destinataire, dans sa session ouverte.

**Annuler** un transfert en transit tant que la session qui l'a envoyé est
ouverte : les billets reviennent dans le tiroir expéditeur (une entrée
d'espèces sur cette session). Un transfert reçu ne peut pas être annulé :
renvoyez les billets. Une fois envoyé, seule la **Note** d'un transfert
peut être modifiée. Les boutons **Mouvements d'espèces** et **Mouvements
de billets** ouvrent ses lignes de relevé et ses pièces et billets.

Les tiroirs d'un bureau
-----------------------

L'onglet **Tiroirs** du bureau de change (administrateurs du Point de
Vente) affiche, pour chaque guichet avec une session ouverte, les
**Espèces attendues** de chaque devise (ouverture, ventes, mouvements
d'espèces, opérations de change et transferts), les **Opérations du
jour** et les **Commissions du jour**, avec les totaux. En dessous,
**Fonds en transit** donne, par devise, les transferts envoyés et pas
encore reçus, leur montant et leur valeur, et le **Total en transit**.

Tableau des taux en PDF
-----------------------

Le tableau des taux décrit plus haut s'imprime aussi en PDF (*Taux de
change*) avec **Imprimer les taux de change** dans les paramètres, ou
depuis le menu *Imprimer* des points de vente (vue liste de *Point de
Vente → Tableau de bord*).

Notes comptables
================

* Une opération correspond à deux lignes de relevé du journal d'espèces
  de la session : les billets reçus (positifs, dans leur devise, à leur
  valeur reçue) et les billets rendus (négatifs, dans leur devise, à leur
  valeur rendue). Une ligne dans la devise du point de vente ne porte
  aucune devise étrangère. Les lignes portent le caissier comme
  partenaire.
* Les deux lignes utilisent le **compte de commission** comme
  contrepartie : la différence entre les deux valeurs, la commission, est
  ce qui reste sur ce compte. Aucune écriture séparée n'est comptabilisée
  pour la commission.
* La **Marge de taux** d'une opération est ce que ses taux rapportent par
  rapport aux taux d'Odoo du jour : valeur des billets reçus au taux
  d'Odoo moins leur valeur reçue, plus la valeur rendue moins la valeur
  des billets rendus au taux d'Odoo. Elle est réalisée comme pour toute
  vente en devise étrangère : par la réévaluation du tiroir de POS
  Multi-Currency Cash, ou lors du dépôt des billets (voir son guide). La
  commission plus la marge de taux est le revenu de l'opération. Avec des
  taux fixes au-dessus des taux d'Odoo, la marge de taux peut être
  négative : elle montre la perte.
* Une annulation comptabilise deux lignes opposées aux lignes d'origine,
  sur le même compte de contrepartie : la commission est contrepassée.
* Les opérations et leurs lignes de relevé ne peuvent pas être supprimées ;
  les références (``EXC/AAAA/NNNNN``) n'ont pas de trou.
* Un transfert de billets correspond lui aussi à deux lignes de relevé :
  une sortie d'espèces sur la session du guichet expéditeur à l'envoi des
  billets, et une entrée d'espèces de même valeur sur la session du
  guichet destinataire à leur réception, toutes deux avec le **Compte de
  fonds en transit** du bureau comme contrepartie. La valeur est le
  montant au taux d'Odoo du jour, dans la devise de la société. Le solde
  du compte est la valeur des billets en transit ; il revient à zéro une
  fois chaque transfert reçu ou annulé.

Mise à jour vers 20.0.4.0.0
===========================

* POS Multi-Currency Cash 20.0.2.1.0 ou plus récent reste requis.
* La mise à jour copie le numéro de licence de change de chaque point de
  vente sur ses opérations existantes, puis chaîne les opérations
  existantes dans le hachage du registre, dans l'ordre de leur création,
  société par société. Lancez **Vérifier l'intégrité** une fois après la
  mise à jour.
* Rien ne change pour un guichet hors de tout bureau de change : ses
  paramètres restent tels quels. Les nouveaux seuils (**Origine des fonds
  obligatoire au-delà de**, **Examen au-delà de**) partent de 0, jamais
  appliqués, et **Suivre les billets par coupure** n'est pas coché.
* Pour utiliser les bureaux, créez-les, ajoutez leurs guichets, puis
  renseignez le **Compte de fonds en transit** de chaque bureau avant
  d'envoyer des billets entre ses guichets.
* Fermez les sessions, ou rechargez chaque caisse, après la mise à jour,
  pour que les caisses chargent les nouvelles entrées du menu.

Mise à jour depuis 20.0.1.x
===========================

* Mettez d'abord à jour POS Multi-Currency Cash en 20.0.2.1.0 ou plus
  récent : l'installation et la mise à jour sont refusées sinon.
* La **Marge de vente de change** de chaque devise prend la valeur de sa
  Marge du taux de caisse (une marge négative devient la marge de vente
  qui garde le même taux de vente, 2,04 % pour -2 %) : les billets rendus
  sont désormais valorisés au taux de vente, en faveur du commerce.
  Vérifiez les marges et le tableau des taux avant d'ouvrir les caisses.
* Les opérations déjà enregistrées reçoivent leur utilisateur, leur
  statut, leur taux, leur marge de taux et le nom du client. Leur marge de
  taux est calculée au taux d'Odoo de leur jour : les opérations
  antérieures montrent la perte de l'ancienne valorisation des billets
  rendus.
* La séquence des références devient sans trou. Les opérations ne peuvent
  plus être supprimées : utilisez **Annuler l'opération**.
* Le tiroir de la devise du point de vente est désormais vérifié : comptez
  son montant d'ouverture.
* Fermez les sessions, ou rechargez chaque caisse, après la mise à jour :
  une caisse encore sur la version précédente ne peut pas enregistrer
  d'opération.
* Une opération dont une ligne de relevé a été supprimée avec 20.0.1.x est
  signalée dans le journal du serveur et par un message sur l'opération :
  corrigez le tiroir par un mouvement d'espèces.

Limites connues
===============

* Le guichet fonctionne en ligne : le calcul et l'enregistrement sont des
  appels au serveur.
* Une opération concerne deux devises ; un client qui change plusieurs
  devises à la fois génère plusieurs opérations.
* Une opération ne peut être annulée que tant que sa session est ouverte,
  et pas dans une période du registre clôturée.
* Les billets ne sont suivis par coupure que pour les devises étrangères :
  la devise du point de vente n'a pas de comptage par pièces et billets.
* Le stock de billets ne suit que les opérations de change et les
  transferts : les ventes en espèces et les mouvements d'espèces dans une
  devise étrangère modifient le tiroir sans coupures. Le comptage suivant
  le corrige.
* Un transfert de billets reçu ne peut pas être annulé : renvoyez les
  billets.
* La vérification d'intégrité couvre le registre de toute la société.

Dépannage
=========

L'entrée Opération de change est absente du menu
------------------------------------------------

Vérifiez que **Opération de change** est activée sur le point de vente,
puis fermez et rouvrez la caisse : le réglage est lu au chargement de ses
données.

Un message s'affiche au lieu de la fenêtre
------------------------------------------

Ajoutez une devise étrangère au mode de paiement espèces du point de
vente, ou renseignez le **Compte de commission** dans la section
*Opération de change* des paramètres, puis rechargez la caisse.

Le compte de commission est refusé
----------------------------------

Seul un compte de type *Revenus* ou *Autres produits* peut recevoir les
commissions.

Le montant rendu est inférieur au montant attendu
-------------------------------------------------

Les billets rendus sont valorisés au taux de vente et arrondis à la baisse
à l'**Arrondi de la monnaie** de leur devise (l'Arrondi du total du point
de vente pour sa propre devise), et la commission inclut le reste.
Vérifiez la Marge de vente de change, l'arrondi et la commission de la
devise.

Le tiroir ne contient pas le montant
------------------------------------

Le tiroir de la devise rendue doit contenir le montant, tel que compté par
le contrôle de clôture. Faites le change dans l'autre sens, ou enregistrez
d'abord une entrée d'espèces dans cette devise. Pour la devise du point de
vente, vérifiez que le montant d'ouverture a été compté.

Un avertissement orange sur les pièces et billets
-------------------------------------------------

Le montant reçu ne peut pas être composé avec les pièces de la devise
(voir *L'avertissement sur les pièces*). Il ne bloque pas l'opération.

« La cotation a changé »
------------------------

Un taux, une marge ou une commission a changé après la cotation : rien
n'a été enregistré. La fenêtre demande aussitôt la nouvelle cotation et
l'affiche avec un avertissement ; vérifiez le nouveau montant avec le
client, puis appuyez à nouveau sur **Confirmer**. L'opération n'est jamais
confirmée d'elle-même.

La connexion a été perdue pendant la confirmation
-------------------------------------------------

Confirmez à nouveau une fois la connexion rétablie : une opération déjà
enregistrée ne l'est pas deux fois.

Une opération ne peut pas être annulée
--------------------------------------

Seul un administrateur du Point de Vente peut annuler, tant que la
session de l'opération est ouverte, et lorsque le tiroir contient encore
les billets reçus. Après la clôture, voir *Annuler une opération*.

La pièce d'identité est refusée
-------------------------------

Type, numéro et date d'expiration sont obligatoires (ou **Sans date
d'expiration** coché pour une pièce qui n'en a pas), et la pièce ne doit
pas être expirée. Le seuil peut être atteint avec les opérations liées du
client : la fenêtre affiche leur total.

Supprimer est absent des opérations
-----------------------------------

Les opérations ne peuvent pas être supprimées, afin que le registre reste
complet : annulez plutôt l'opération.

Envoyer des billets et Recevoir des billets sont absents
--------------------------------------------------------

Le guichet doit appartenir à un bureau de change avec au moins un autre
guichet où **Opération de change** est activée. Rechargez ensuite la
caisse.

« Définissez le compte de fonds en transit »
--------------------------------------------

Renseignez le **Compte de fonds en transit** du bureau de change (un
compte d'actifs circulants) avant de transférer des billets.

Les billets ne correspondent pas au montant
-------------------------------------------

Avec les billets suivis, le **Total** de chaque grille doit être égal au
montant de l'opération ou du transfert. Corrigez les quantités.

« Il manque ... dans le tiroir »
--------------------------------

Le stock du tiroir, tel que compté à l'ouverture et déplacé par les
opérations, contient moins de ces billets. Vérifiez les billets
réellement rendus ou envoyés. Cela ne bloque pas l'opération.

Le registre ne peut pas être clôturé
------------------------------------

La période doit être terminée, les sessions de ses opérations clôturées,
et la vérification d'intégrité réussie. Elle ne doit pas chevaucher une
clôture du même bureau ou de toute la société ; une clôture de toute la
société ne doit chevaucher aucune clôture d'un bureau. Pour clôturer toute la société,
laissez **Bureau de change** et **Points de vente** vides.

Le caissier ne trouve pas Opérations de change ou Registre de change
--------------------------------------------------------------------

Ces menus sont réservés aux administrateurs du Point de Vente. Les
caissiers utilisent l'entrée **Opérations de change** du menu de la
caisse.

Avertissement
=============

Ce module est fourni par Natimai Solutions sous l'Odoo Proprietary License
v1.0. Les opérations de change peuvent être réglementées dans votre pays
(agrément, identification du client, registres, déclarations) : le module
vous aide à conserver les opérations, leur client et sa pièce d'identité
ainsi que le registre de change, mais il ne rend pas à lui seul votre
activité conforme ; la conformité aux réglementations locales reste de la
responsabilité de l'entreprise.

Support
=======

* E-mail : odoo@natimai.solutions
* Site web : https://www.natimai.solutions

Licence
=======

OPL-1 (Odoo Proprietary License), voir le fichier ``LICENSE`` du module.
