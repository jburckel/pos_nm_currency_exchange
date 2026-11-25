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
* un responsable peut annuler une opération erronée tant que la session est
  ouverte ;
* les opérations apparaissent dans le contrôle de clôture, dans le rapport
  *Position de change* et dans le rapport *Détails des ventes*, dans une
  liste avec un tableau croisé des commissions et des marges de taux, et
  dans un registre de change exportable ou imprimable pour une période ;
* le tableau des taux du guichet peut être affiché et imprimé à la caisse,
  ou imprimé en PDF.

Prérequis
=========

* L'application **Point de Vente** (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) **20.0.2.1.0 ou
  plus récent**, vendu séparément, avec au moins une devise étrangère sur
  le mode de paiement espèces du point de vente (voir son guide : *Accepter
  une devise en espèces*). Une version plus ancienne de POS Multi-Currency
  Cash ne fonctionne pas avec ce module : mettez-la à jour d'abord.
* Un **compte de produits pour les commissions** (type *Revenus* ou
  *Autres produits*).

Configuration
=============

Activer le guichet
------------------

Allez dans *Point de Vente -> Configuration -> Paramètres*, sélectionnez
votre point de vente et repérez la section **Opération de change** :

* **Opération de change** (activée par défaut) : affiche les entrées du
  guichet dans le menu de la caisse.
* **Compte de commission** : compte de produits qui reçoit les
  commissions. Seuls les comptes de produits peuvent être choisis. Il est
  requis pour enregistrer une opération.
* **Numéro de licence de change** : numéro de licence ou d'enregistrement
  de votre activité de change, imprimé sur les tickets et le tableau des
  taux lorsqu'il est renseigné.
* **Client obligatoire au-delà de** : valeur d'une opération, dans la
  devise du point de vente, au-delà de laquelle le client doit être
  identifié.
* **Client obligatoire pour chaque opération** : chaque opération nomme
  son client.
* **Pièce d'identité obligatoire au-delà de** : valeur au-delà de laquelle
  la pièce d'identité du client est enregistrée sur l'opération.
* **Période des opérations liées (jours)** : lorsqu'elle est supérieure à
  0, la valeur comparée aux deux seuils est l'opération plus les opérations
  du même client sur ce nombre de jours (voir *Identification du client*).
* **Imprimer les taux de change** : imprime le tableau des taux du point de
  vente en PDF.

Les seuils à 0 ne sont jamais appliqués.

Commissions et marge de vente par devise
----------------------------------------

Allez dans *Point de Vente -> Configuration -> Devises en espèces* et
ouvrez la ligne de la devise. Le groupe *Opération de change* contient
quatre valeurs, les montants étant dans la devise du point de vente :

* **Marge de vente de change (%)** : marge du guichet sur les billets de
  cette devise qu'il rend (voir *Taux* ci-dessous). Masquée avec un taux de
  caisse fixe, où elle n'est pas utilisée ;
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
euros à 2,20 EUR pour 1 USD (100 EUR reçus valent 45,45 $) et les vend à
1,82 EUR pour 1 USD (100 EUR rendus valent 55,00 $), avant la commission.

L'écart avec les taux d'Odoo est la **Marge de taux** de l'opération (voir
*Notes comptables*). Lors d'une mise à jour depuis une version antérieure
à 20.0.2.0.0, la Marge de vente de change de chaque devise prend la valeur
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
activité doit présenter au client.

Qui peut faire quoi
-------------------

* Les **utilisateurs du Point de Vente** (caissiers) enregistrent les
  opérations à la caisse, réimpriment leurs tickets et affichent le tableau
  des taux. Ils peuvent lire les opérations mais pas les modifier.
* Les **administrateurs du Point de Vente** (accès *Point de Vente* :
  *Administrateur*) voient en plus les menus *Point de Vente -> Commandes
  -> Opérations de change* et *Point de Vente -> Analyse -> Registre de
  change* et les pièces d'identité des clients, peuvent modifier la note
  d'une opération et annuler une opération.
* Personne ne peut supprimer une opération ni l'une de ses lignes de
  relevé.
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
   numéro et date d'expiration sont obligatoires. **Nationalité** et
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
* la cotation a changé entre la fenêtre et le serveur (taux, marge ou
  commission modifiés entre-temps) : « La cotation a changé : ... ».
  Saisissez à nouveau le montant pour obtenir la nouvelle cotation, puis
  confirmez ;
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
devise du point de vente (100 EUR, 10 000 XPF, 1 000 000 VND). Les montants
sont calculés par la cotation du guichet : ils correspondent aux
opérations. **Imprimer** imprime le tableau sur l'imprimante de tickets.

Annuler une opération
---------------------

Une opération erronée s'annule, elle ne se corrige pas par une autre
opération : une opération inverse prélèverait à nouveau la commission et
arrondirait à nouveau les billets, et un mouvement d'espèces laisserait la
commission sur le compte de commission.

Un administrateur du Point de Vente ouvre l'opération (*Point de Vente ->
Commandes -> Opérations de change*), appuie sur **Annuler l'opération**,
puis confirme. C'est possible tant que la session de l'opération est
ouverte et que le tiroir contient encore les billets reçus (le client les
récupère). Deux lignes de relevé exactement opposées aux lignes d'origine
sont comptabilisées sur la session : mêmes montants dans les deux devises,
même compte de contrepartie. Les deux tiroirs et le compte de commission
reviennent à leur état d'avant l'opération.

L'opération passe à **Annulée**, avec la date et l'utilisateur, un message
est publié sur la session et sur l'opération, et elle ne compte plus dans
les commissions, le résumé de clôture et les rapports. Son ticket,
réimprimé, est marqué *ANNULÉ*.

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
  délivrance, date d'expiration, nationalité et date de naissance. Une
  pièce expirée est refusée.

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

*Point de Vente -> Commandes -> Opérations de change* (administrateurs du
Point de Vente) liste les opérations avec leur référence, leur date, le
point de vente, le caissier, le client, les billets reçus et rendus, la
commission, la marge de taux et le statut. La liste s'ouvre avec le filtre
**Effectuée** ; le filtre **Annulée** affiche les opérations annulées.
Autres filtres : *Aujourd'hui*, *Avec client*, *Achat de devises*, *Vente
de devises*, *Change croisé* ; regroupement par point de vente, session,
caissier, type d'opération, statut, devise ou date. Le tableau croisé
donne les commissions, marges de taux et valeurs reçues par jour, statut
et devise.

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

Seule la **Note** peut être modifiée, par un administrateur du Point de
Vente ; ses modifications sont consignées dans le chatter.

La fiche de session dispose d'un bouton avec le total des commissions et
« Opérations : N », le nombre d'opérations effectuées ; il les ouvre.

Détails des ventes
------------------

Le rapport *Détails des ventes* se termine par un tableau *Opération de
change* : chaque opération avec sa session, ses montants, sa commission et
sa marge de taux, puis les totaux, une ligne par devise des points de
vente, et la liste des opérations annulées, qui ne sont pas comptées.
Imprimé depuis une session, il couvre les opérations de la session ; lancé
depuis *Point de Vente -> Analyse -> Détails des ventes* pour une période,
il couvre les opérations datées de cette période sur les points de vente
sélectionnés (tous lorsqu'aucun n'est sélectionné), sessions ouvertes
comprises. Le rapport *Position de change* de POS Multi-Currency Cash
reflète les billets déplacés.

Registre de change
------------------

*Point de Vente -> Analyse -> Registre de change* (administrateurs du
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

Tableau des taux en PDF
-----------------------

Le tableau des taux décrit plus haut s'imprime aussi en PDF (*Taux de
change*) avec **Imprimer les taux de change** dans les paramètres, ou
depuis le menu *Imprimer* des points de vente (vue liste de *Point de
Vente -> Tableau de bord*).

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
* Une opération ne peut être annulée que tant que sa session est ouverte.
* Le tableau des taux n'est pas affiché sur l'écran client.

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

Un taux, une marge ou une commission a changé après la cotation.
Saisissez à nouveau le montant : la fenêtre calcule le nouveau montant,
puis confirmez.

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

Type, numéro et date d'expiration sont obligatoires, et la pièce ne doit
pas être expirée. Le seuil peut être atteint avec les opérations liées du
client : la fenêtre affiche leur total.

Supprimer est absent des opérations
-----------------------------------

Les opérations ne peuvent pas être supprimées, afin que le registre reste
complet : annulez plutôt l'opération.

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
