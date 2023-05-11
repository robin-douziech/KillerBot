import discord

members_file = "json/members.json"
missions_file = "json/missions.json"
events_file = "json/events.json"
vars_file = "json/vars.json"
infos_file = "json/infos.json"

bot_guild_id = 1064187729597976616
bot_channel_id = 1091091154734432318
log_channel_id = 1095407436757737614
gazette_channel_id = 1101924745945026601

bot_owner_id = 394185214479302656

start_game_regexp = r"D[ée]but de la partie"
stop_game_regexp = r"Fin de la partie"
registration_regexp = r"[Mm]ission : (.*)"
unregistration_regexp = r"[Jj]e ne veux plus jouer"
killer_found_regexp = r"[Mm]on killer est (.*)"
death_regexp = r"0xdeaddead"
rules_regexp = r".*[Rr][èe]gles.*"
too_hard_regexp = r".*[Mm]ission.*trop difficile.*"

rules_msg_list = []

for i in range(50) :
	rules_msg_list.append(["", None])



##########################################################################################################


rules_msg_list[0][0] = """
**Voici les règles du Killer dans leur intégralité :**

__Tout d'abord, laissez-moi vous présenter les **règles de base** pour comprendre le but du jeu__ :

Au début de la partie, chaque joueur reçoit une mission et une cible (cette cible est l'un des autres joueurs).
Le but du jeu est d'être la dernière personne encore en vie. Pour cela, il va falloir éliminer tous les autres joueurs, à commencer par sa cible.
Pour tuer votre cible, il vous suffit de réaliser la mission qui vous a été confiée (cette mission implique votre cible, il faut généralement lui faire faire quelque chose sans qu'elle devine que vous êtes en train de réaliser votre mission).
Une fois que vous avez réalisé votre mission, votre cible meurt. Elle est éliminée de la partie et vous récupérez sa mission et sa cible.
La partie continue jusqu'à ce qu'il ne reste qu'un joueur en vie.\n\u200B
"""


##########################################################################################################


rules_msg_list[1][0] = """
__Maintenant que vous avez compris le but du jeu, laissez-moi vous apporter **quelques précisions**__ :

À tout moment de la partie, chaque joueur encore en vie possède une cible et une mission, mais aussi un "killer" (un autre joueur l'ayant pour cible dont il ne connait évidemment pas l'identité).
En plus d'essayer de tuer votre cible en réalisant votre mission, il est aussi possible de tenter de démasquer votre killer.
Si vous pensez connaître l'identité de votre killer, vous pouvez me la communiquer. Si vous avez raison, votre killer meurt et son killer récupère sa cible (donc vous) mais garde sa mission, mais si vous vous trompez, c'est vous qui mourez et votre killer récupère votre mission.

Il y a donc trois façons différentes de mourir dans le killer :
- se faire tuer par son killer s'il réussit à réaliser sa mission
- se faire tuer par sa cible si elle réussit à deviner votre identité
- mourir tout seul en se trompant sur l'identité de son killer (dommage)\n\u200B
"""


##########################################################################################################


rules_msg_list[2][0] = """
Laissez-moi maintenant vous expliquer le **déroulement d'une partie** :

__***I. Avant la partie : inscription et désinscription***__

Pour vous inscrire à une partie de Killer, il suffit de m'envoyer en message privé une mission qui sera distribuée à un des joueurs de la partie (comme ça, chaque joueur de la partie connait exactement une des missions présentes dans la partie, ça évite qu'il y ait un joueur qui connaisse toutes les missions de la partie).
Votre message devra être de la forme "Mission : <votre mission>". Si vous êtes inscrit à une partie et voulez changer la mission proposée, il suffit de renvoyer un message de la même forme en changeant la mission.

Par exemple, pour m'inscrire, je peux envoyer le message suivant au bot :
"""

with open('images/image1.png', 'rb') as f :
	image1 = discord.File(f)
rules_msg_list[2][1] = image1


##########################################################################################################


rules_msg_list[3][0] = """
Et si je veux changer la mission proposée :
"""

with open('images/image2.png', 'rb') as f :
	image2 = discord.File(f)
rules_msg_list[3][1] = image2


##########################################################################################################


rules_msg_list[4][0] = """\n\u200B
Quelques règles que votre mission devra respecter :

- votre mission doit comprendre une action faite par sa cible. Par exemple, "boire un verre d'eau" n'est pas une mission valide car elle n'implique que le personne que recevra cette mission.
- votre mission ne doit pas comprendre d'action faite par une autre personne que sa cible. Par exemple, "faire en sorte que votre cible arrose Louis avec un verre d'eau" n'est pas une mission valide car la cible de la mission peut être Louis
- votre mission peut comprendre une action faite par la personne qui recevra cette mission. Par exemple, "faire en sorte que votre cible vous serve un vers d'eau" est une mission valide
- votre mission ne doit pas être compliquée (j'en profite pour vous informer que vous avez la même chance de tomber sur votre propre mission que tous les autres joeurs). Par exemple, "Faire en sorte que votre cible fasse un triple saut périlleux en chantant du yodel" n'est pas une mission valide.
- votre mission doit être claire, sons sens ne doit pas pouvoir être interprété de différentes manières.

Si vous êtes inscrits à une partie et voulez vous désinscrire de celle-ci, envoyez-moi "Je ne veux plus jouer" en message privé :
"""

with open('images/image3.png', 'rb') as f :
	image3 = discord.File(f)
rules_msg_list[4][1] = image3


##########################################################################################################


rules_msg_list[5][0] = """\n\u200B
__***II. Pendant la partie***__

1) __Si vous voulez tenter de démasquer votre killer__

Envoyez-moi un message de la forme "Mon killer est <pseudo du killer>". Le pseudo du killer doit être de la forme <pseudo>#<identifiant> (ex: M1k3y#8407), mais ne vous inqiétez pas, vous ne mourrez pas si vous faites une faute de frappe, votre message ne sera pris en compte que si le pseudo renseigné correspond bien au pseudo d'un membre du serveur.

Exemple :
"""

with open('images/image4.png', 'rb') as f :
	image4 = discord.File(f)
rules_msg_list[5][1] = image4


##########################################################################################################


rules_msg_list[6][0] = """
Autre exemple :
"""

with open('images/image5.png', 'rb') as f :
	image5 = discord.File(f)
rules_msg_list[6][1] = image5


##########################################################################################################


rules_msg_list[7][0] = """\n\u200B
2) __Si vous avez réalisé votre mission__

Si vous avez réalisé la mission qui vous a été confiée, envoyez-moi "gotcha". Je demanderai alors confirmation à votre cible en lui envoyant votre identité et votre mission (donc réfléchissez bien avant de m'envoyer "gotcha" : si votre cible peut contester le fait que vous ayez réalisé votre mission, vous aurez des proclèmes ... )

3) __Des événements pour pimenter les parties__

Chaque jour, un nouvel événement aura lieu pour débloquer la partie et pour que toutes les parties ne se ressemblent pas.
Ces événements pourront aussi faire participer les joueurs éliminés de la partie.
Je ne vous en dit pas plus pour le moment sur ces événements, je vous laisse les découvrir pendant la partie.
"""


##########################################################################################################


rules_msg_list[8][0] = """

__**III. Après la partie**__

Une autre partie.\n\u200B
"""


rules_msg_list[9][0] = """\n\u200B
Les parties dureront sûrement 5 jours ou 12 jours (du lundi matin au samedi matin). Vous aurez donc en général un week-end pour vous inscrire si vous voulez jouer (on ne peux pas s'inscrire à la prochaine partie si une partie est en cours, il faut attendre la fin de la partie en cours, désolé).
"""

rules_msg = """

:skull::skull::skull::skull: Bienvenue dans le Killer ! :skull::skull::skull::skull:


Je suis **KillerBot**, l'arbitre de ce jeu.


**Voici les principales règle du jeu :**

- chaque participant se voit attribuer une cible et une mission impliquant cette cible

- le but du jeu : mener sa mission à bien pour tuer sa cible

- quand on réussi à tuer sa cible, on récupère sa mission (et sa cible)

- le dernier joueur en vie gagne la partie

Si vous voulez plus de précisions, demandez-moi les règles en message privé
"""