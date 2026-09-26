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
  choisit la devise reçue et la devise rendue, et saisit le montant reçu ;
* la caisse calcule le montant à rendre aux taux de caisse du point de
  vente, avec la commission de la devise et l'arrondi à ses pièces et
  billets ;
* l'opération est enregistrée avec le caissier et, lorsque c'est requis, le
  client, et un ticket de change est imprimé ;
* les deux tiroirs bougent : les billets reçus entrent dans le tiroir de
  leur devise et les billets rendus sortent de l'autre, sur le journal
  d'espèces de la session, avec la commission comptabilisée sur un compte
  de produits dédié ;
* les opérations apparaissent dans le contrôle de clôture, dans le rapport
  *Position en devises* et dans le rapport *Détails des ventes*, et sont
  listées par point de vente, session et caissier avec un tableau croisé
  des commissions.

Prérequis
=========

* L'application **Point de Vente** (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) 20.0, avec au
  moins une devise étrangère sur le mode de paiement espèces du point de
  vente (voir son guide : *Accepter une devise en espèces*).
* Un **compte de produits pour les commissions**.

Configuration
=============

Activer le guichet
------------------

Allez dans *Point de Vente -> Configuration -> Paramètres*, sélectionnez
votre point de vente et repérez la section **Opération de change** :

* **Opération de change** (activée par défaut) : affiche l'entrée dans le
  menu de la caisse.
* **Compte des commissions de change** : compte de produits qui reçoit les
  commissions. Il est requis pour enregistrer une opération.
* **Client obligatoire au-delà de** : valeur d'une opération, dans la
  devise du point de vente, au-delà de laquelle le client doit être
  identifié. 0 : jamais.

Commissions par devise
----------------------

Allez dans *Point de Vente -> Configuration -> Devises de caisse* et ouvrez
la ligne de la devise. Le groupe *Opération de change* contient trois
valeurs, toutes dans la devise du point de vente sauf le pourcentage :

* **Commission de change (%)** : pourcentage de la valeur des billets
  reçus ;
* **Commission de change fixe** : partie fixe ajoutée au pourcentage ;
* **Commission de change minimale** : la commission est au moins ce
  montant.

La commission d'une opération est celle de la devise étrangère concernée
(la devise rendue lorsque les deux sont étrangères). Chaque modification
des commissions est consignée dans le chatter de la ligne, comme les taux.

Taux et pièces et billets
-------------------------

Le guichet utilise les taux de caisse de POS Multi-Currency Cash : les
billets reçus sont valorisés au taux appliqué à ce que paie un client
(taux d'Odoo avec la marge, ou le taux fixe), les billets rendus au taux
appliqué à la monnaie (le taux de rendu fixe lorsqu'il est défini). Les
billets rendus sont arrondis *à la baisse* à l'**Arrondi du rendu** de leur
devise, de sorte que le caissier n'ait jamais à rendre des pièces qui
n'existent pas dans le tiroir ; le reste demeure dans la commission.

Travail quotidien
=================

Échanger des devises
--------------------

Depuis n'importe quel écran de la caisse, ouvrez le menu (en haut à
droite) et appuyez sur **Opération de change** :

1. choisissez la devise **reçue du client** et saisissez le montant ;
2. choisissez la devise **rendue** ; le montant, le taux appliqué
   (commission incluse) et la commission sont calculés au fur et à mesure
   de la saisie. Le bouton flèche échange les deux devises ;
3. lorsque la valeur des billets reçus dépasse le seuil du point de vente,
   appuyez sur **Client** et choisissez le client (créez-le si besoin) ; le
   bouton reste rouge tant que ce n'est pas fait ;
4. ajoutez une note si utile, puis **Confirmer**. Le tiroir-caisse
   s'ouvre, le ticket de change s'imprime (reçu, rendu, taux, commission)
   et une notification résume l'opération.

La caisse refuse une opération lorsque le tiroir de la devise rendue ne
contient pas assez de billets, lorsque le montant est trop petit pour un
seul billet, ou lorsque la même devise est choisie des deux côtés.

Clôture de la session
---------------------

La fenêtre de clôture affiche un bloc **Opération de change** avec le
nombre d'opérations, chaque opération (reçu, rendu, caissier) et le total
des commissions. Les billets reçus et rendus sont déjà compris dans les
montants attendus de leurs devises : un change est une entrée d'espèces
sur un tiroir et une sortie sur l'autre, toutes deux listées dans les
mouvements de la devise.

Consulter les opérations
------------------------

*Point de Vente -> Commandes -> Opérations de change* liste chaque
opération avec sa référence, sa date, le point de vente, la session, le
caissier, le client, les billets reçus et rendus, le taux et la
commission ; regroupez par point de vente, session, caissier ou devise, et
passez au tableau croisé pour les commissions par jour et par devise. La
fiche de session dispose d'un bouton **Opérations de change** avec le
total des commissions.

Le rapport *Détails des ventes* d'une session se termine par un tableau
*Opération de change* (opérations et commissions), et le rapport
*Position en devises* de POS Multi-Currency Cash reflète les billets
déplacés.

Notes comptables
================

* Une opération correspond à deux lignes de relevé du journal d'espèces
  de la session : les billets reçus (positifs, dans leur devise, valorisés
  au taux de caisse) et les billets rendus (négatifs, dans leur devise,
  valorisés au taux de rendu). Une ligne dans la devise du point de vente
  ne porte aucune devise étrangère.
* Les deux lignes utilisent le **compte des commissions de change** comme
  contrepartie : la différence entre les deux valeurs, la commission, est
  ce qui reste sur ce compte. Aucune écriture séparée n'est comptabilisée
  pour la commission.
* La marge entre les taux de caisse et les taux d'Odoo est réalisée comme
  pour toute vente en devise étrangère : lors du dépôt des billets ou de
  la réévaluation du tiroir (voir le guide de POS Multi-Currency Cash).
* Les opérations peuvent être ouvertes depuis leur fiche (bouton *Lignes
  de relevé*) et ne peuvent pas être modifiées ; une opération erronée est
  corrigée par une opération inverse ou un mouvement de caisse.

Limites connues
===============

* Le guichet fonctionne en ligne : le calcul et l'enregistrement sont des
  appels au serveur.
* Une opération concerne deux devises ; un client qui change plusieurs
  devises à la fois génère plusieurs opérations.
* Le ticket est imprimé par l'imprimante de tickets de la caisse ou par le
  navigateur ; il n'y a pas d'envoi par e-mail du ticket de change.

Dépannage
=========

L'entrée Opération de change est absente du menu
------------------------------------------------

Vérifiez que **Opération de change** est activée sur le point de vente,
puis fermez et rouvrez la caisse : le réglage est lu au chargement de ses
données.

L'opération est refusée pour le compte des commissions de change
----------------------------------------------------------------

Renseignez le **Compte des commissions de change** dans la section
*Opération de change* des paramètres du point de vente.

Le montant rendu est inférieur au montant attendu
-------------------------------------------------

Les billets rendus sont arrondis à la baisse à l'**Arrondi du rendu** de
leur devise, et la commission inclut le reste. Diminuez l'arrondi sur la
devise, ou vérifiez sa commission.

Avertissement
=============

Ce module est fourni par Natimai Solutions sous l'Odoo Proprietary License
v1.0. Les opérations de change peuvent être réglementées dans votre pays
(agrément, identification du client, registres) : le module enregistre les
opérations et leur client, mais la conformité aux réglementations locales
reste de la responsabilité de l'entreprise.

Support
=======

* E-mail : odoo@natimai.solutions
* Site web : https://www.natimai.solutions

Licence
=======

OPL-1 (Odoo Proprietary License), voir le fichier ``LICENSE`` du module.
