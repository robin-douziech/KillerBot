from discord.ext import commands
import discord
import json
import re
import sys
import random
import asyncio
import logging

from variables import *

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,  # Niveau de journalisation (par exemple : logging.INFO, logging.DEBUG)
    format='[%(asctime)s] %(levelname)s - %(message)s',  # Format du message de log
    datefmt='%Y-%m-%d %H:%M:%S'  # Format de la date/heure
)

class KillerBot(commands.Bot) :

	def __init__(self, members_file, missions_file, events_file, vars_file, infos_file) :
		super().__init__(command_prefix="!", intents=discord.Intents.all())

		# members JSON
		self.members_file = members_file
		self.members = {}

		# missions JSON
		self.missions_file = missions_file
		self.missions = {}

		# events JSON
		self.events_file = events_file
		self.events = {}

		# variables JSON
		self.vars_file = vars_file
		self.vars = {}

		# infos JSON
		self.infos_file = infos_file
		self.infos = {}

	def log(self, message) :
		logging.info(message)

	async def flash_info(self) :

		limit = self.vars['deaths_annouce_limit']
		nb_deaths = 0
		state = ""

		# avant/pendant/après l'arrêt de l'annonce des morts
		if len(self.vars['players_alive']) > limit :
			state = "before"

		elif len(self.vars['players_alive']) <= limit and self.vars['kills_count']+len(self.vars['players_alive']) > limit :
			state = "end"

		elif self.vars['kills_count']+len(self.vars['players_alive']) <= limit :
			state = "after"

		# nombre de morts à annoncer
		if len(self.vars['players_alive']) >= limit :
			nb_deaths = self.vars['kills_count']

		elif len(self.vars['players_alive']) < limit and self.vars['kills_count']+len(self.vars['players_alive']) > limit :
			nb_deaths = self.vars['kills_count'] - (limit - len(self.vars['players_alive']))

		elif len(self.vars['players_alive']) < limit and self.vars['kills_count']+len(self.vars['players_alive']) <= limit :
			nb_deaths = 0

		msg = f"**[FLASH INFO]** - "
		if state in ["before", "end"] :
			if nb_deaths == 0 :
				msg += f"Aucune mort à déclarer sur la dernière période de jeu. Il reste toujours {max(len(self.vars['players_alive']),limit)} joueurs en vie"
			elif nb_deaths > 0 and state == "end" :
				msg += f"{nb_deaths} personne{'s' if nb_deaths > 1 else ''} (ou peut-être plus) {'sont' if nb_deaths > 1 else 'est'} morte{'s' if nb_deaths > 1 else ''} depuis la dernière fois. Il reste maintenant {limit} joueurs en vie (ou peut-être moins). A partir de maintenant j'arrête d'annoncer les morts."
			else :
				msg += f"{nb_deaths} personne{'s' if nb_deaths > 1 else ''} {'sont' if nb_deaths > 1 else 'est'} morte{'s' if nb_deaths > 1 else ''} depuis la dernière fois. Il reste maintenant {len(self.vars['players_alive'])} joueurs en vie."

		elif state == "after" :
			liste_info = list(self.infos['liste_info_pourries'])
			if len(liste_info) > 0 :
				info = liste_info[random.randint(0,len(liste_info)-1)]
				msg += f"__{info}__\n{self.infos['liste_info_pourries'][info]}"
				self.infos['liste_info_pourries'].pop(info)
			else :
				msg += f"Non rien."

		self.vars['kills_count'] = 0

		self.write_infos()
		self.write_vars()

		await self.bot_channel.send(msg)
		self.log(f"flash info envoyé ! state: {state} / nb_deaths: {nb_deaths}")

	def dump_circle(self, player_list) :

		msg = f""
		for member in player_list :
			msg += f"{member} => {self.members[member]['target']}\n"
		return msg

	#===============================#
	# WRINTING THINGS IN JSON FILES #
	#===============================#

	def write_members(self) :

		""" Writes the content of self.members in the members_file in JSON format
		"""

		json_object = json.dumps(self.members, indent=2)
		with open(self.members_file, "wt") as f_members :
			f_members.write(json_object)

	def write_missions(self) :

		""" Writes the content of self.missions in the missions_file in JSON format
		"""

		json_object = json.dumps(self.missions, indent=2)
		with open(self.missions_file, "wt") as f_missions :
			f_missions.write(json_object)

	def write_events(self) :

		""" Writes the content of self.events in the events_file in JSON format
		"""

		json_object = json.dumps(self.events, indent=2)
		with open(self.events_file, "wt") as f_events :
			f_events.write(json_object)

	def write_vars(self) :

		""" Writes the content of self.vars in the vars_file in JSON format
		"""

		json_object = json.dumps(self.vars, indent=2)
		with open(self.vars_file, "wt") as f_vars :
			f_vars.write(json_object)

	def write_infos(self) :

		""" Writes the content of self.vars in the vars_file in JSON format
		"""

		json_object = json.dumps(self.infos, indent=2)
		with open(self.infos_file, "wt") as f_infos :
			f_infos.write(json_object)


	#===============================================#
	# SENDING INFORMATIONS AND QUESTIONS TO MEMBERS #
	#===============================================#

	async def informer(self, message) :

		""" Informs that <message> people wanted to be informed (and adds <message> to self.vars['gazette'])
		"""

		# on ajoute le message à la gazette
		self.vars["gazette"].append(message)
		self.write_vars()

		# on informe les abonnés :)
		for member in self.members :
			if "info" in self.members[member]["tags"] :
				await self.fetch_member(member).dm_channel.send(message)

		self.log(f"information envoyée aux abonnés de la gazette !")

	async def send_info_msg(self, member) :

		""" Sends self.vars['gazette'] to member
		"""

		for info_msg in self.vars['gazette'] :
			await self.fetch_member(member).dm_channel.send(info_msg)

		self.log(f"gazette envoyée à {member} !")

	async def send_next_question(self, member) :

		Member = self.fetch_member(member)

		# on n'envoie pas la question suivante si une question est déjà en attente de réponse
		if not(self.members[member]["questioned"]) :

			# s'il y a bien au moins une question à poser ...
			if len(self.members[member]["other_questions"]) > 0 :

				question = self.members[member]["other_questions"][0]

				# on passe à la question suivante
				self.members[member]["current_question"] = question
				self.members[member]["other_questions"] = self.members[member]["other_questions"][1:]

				# switch (question)
				if question == "get informed ?" :
					await Member.dm_channel.send("Veux-tu être tenu(e) au courant des prochains événements de la partie en cours ? [Oui/Non]")
				elif question == "info message ?" :
					await Member.dm_channel.send("Veux-tu que je t'envoie un exemplaire de la gazette des gens morts (récapitulatif de tous les événements de la partie en cours) ? [Oui/Non]")
				elif question == "gotcha ?" :
					killer = self.find_killer(member)
					mission = self.members[killer]["mission to do"][::-1]
					await Member.dm_channel.send(f"Ton killer penses avoir réalisé sa mission.\nVoici son identité : {killer}\nEt voici sa mission : {mission}\nAs-t-il réalisé cette mission ? [Oui/Non]")
				elif re.match(r"gotcha ville fantôme ([^ ].*[^ ]) \?", question) :
					match = re.match(r"gotcha ville fantôme ([^ ].*[^ ]) \?", question)
					await Member.dm_channel.send(f"Un mort t'ayant pour cible penses avoir réalisé sa mission.\nVoici son identité : {match.group(1)}\nEt voici sa mission : {self.events['ville fantôme'][match.group(1)]['mission'][::-1]}\nAs-t-il réalisé cette mission ? [Oui/Non]")
				elif re.match(r"gotcha paranoïa ([^ ].*[^ ]) \?", question) :
					match = re.match(r"gotcha paranoïa ([^ ].*[^ ]) \?", question)
					await Member.dm_channel.send(f"{match.group(1)} penses avoir réalisé sa mission sur toi.\nVoici sa mission : {self.members[match.group(1)]['mission to do'][::-1]}\nAs-t-il réalisé cette mission ? [Oui/Non]")

				self.members[member]["questioned"] = True

				self.log(f"Question suivante envoyée !")

			else :

				self.members[member]["questioned"] = False
				self.members[member]["current_question"] = ""

				self.log(f"Pas de question suivante !")

		else :

			self.log(f"Question suivante non envoyée !")

		self.write_members()

	async def send_rules(self, member) :

		Member = self.fetch_member(member)

		for msg in rules_msg_list :
			if msg[0] != "" :
				await Member.dm_channel.send(msg[0], file=msg[1])

		self.log(f"Règles envoyées à {member}")

	##############
	# ÉVÉNEMENTS #
	##############

	def choose_event(self) :

		chapeau = []
		for event in self.events :
			if self.events[event]["active"] :
				for i in range(self.events[event]["proba"][int(self.vars['day'])-1]) :
					chapeau.append(event)
		self.log(f"choose_event ===> {chapeau[random.randint(0,len(chapeau)-1)]}")
		return chapeau[random.randint(0,len(chapeau)-1)]

	async def process_event(self) :

		event = self.vars["event"]

		self.log(f"process_event ===> {event}")

		if event == "rumeurs" :
			msg_channel = f"**[Événement quotidien : rumeurs]**\n"
			msg_channel += f"Aujourd'hui, chaque joueur (vivant ou mort) va pouvoir répandre anonymement une rumeur, qu'elle soit réelle ou totalement fausse."
			msg_channel += f"Les joueurs ont jusqu'à 12:00 pour m'envoyer la rumeur qu'ils souhaitent répandre. À 12:30, je partagerai toutes les rumeurs ici-même"
			await self.bot_channel.send(msg_channel)
			msg_members =  f"**[Événement quotidien : rumeurs]**\n"
			msg_members += f"Aujourd'hui, comme chaque joueur de la partie en cours, tu vas pouvoir tenter de répandre une rumeur."
			msg_members += f"Celle-ci peut concerner n'importe quoi, la seule limite est ton imagination."
			msg_members += f"Tu peux même citer un membre du serveur (en restant bienveillant, bien évidemment).\n"
			msg_members += f"Pour choisir ta rumeur, envoie-moi \"Rumeur : <ta rumeur>\"\n"
			msg_members += f"Tu as jusqu'à 12:00 pour m'envoyer ta rumeur. A 12:30, je partagerai toutes les rumeurs (sans dire qui les a écrite, bien sûr)"
			for member in self.members :
				if self.members[member]["state"] in ["en vie", "mort"] :
					await self.fetch_member(member).dm_channel.send(msg_members)

		elif event == "killer guess" :
			msg_channel =  f"**[Événement quotidien : killer guess]**\n"
			msg_channel += f"Aujourd'hui, chaque joueur en vie va pouvoir me communiquer l'identité d'un autre joueur qu'il soupçonne d'être son killer."
			msg_channel += f"Les joueurs ont jusqu'à 12:00 pour me donner l'identité d'un autre joueur."
			msg_channel += f"À 12:30 je partagerai dans ce salon le nombre de joueurs m'ayant donné la véritable identité de son killer."
			await self.bot_channel.send(msg_channel)
			msg_members =  f"**[Événement quotidien : killer guess]**\n"
			msg_members += f"Aujourd'hui, tu vas pouvoir me communiquer l'identité d'un joueur que tu penses être ton killer."
			msg_members += f"Tu as jusqu'à 12:00 pour le faire en m'envoyant \"killer guess : <killer>\"."
			msg_members += f"À 12:30, je partagerai dans mon channel le nombre de joueur ayant trouvé la vraie identité de son killer.\nBonne chance"
			for member in self.members :
				if self.members[member]["state"] == "en vie" :
					await self.fetch_member(member).dm_channel.send(msg_members)

		elif event == "paranoïa" :
			msg_channel =  f"**[Événement quotidien : paranoïa]**\n"
			msg_channel += f"Aujourd'hui, tout le monde est la cible de tout le monde, et tout le monde est le killer de tout le monde. "
			msg_channel += f"Tous les joueurs en vie peuvent réaliser leur mission sur n'importe quel joueur qu'il pensent encore en vie. "
			msg_channel += f"Il est bien sûr interdit de réaliser sa mission sur un joueur dont on sait qu'il est mort. "
			await self.bot_channel.send(msg_channel)
			msg_members_vivants =  f"**[Événement quotidien : paranoïa]**\n"
			msg_members_vivants += f"Aujourd'hui, tout le monde est la cible de tout le monde, et tout le monde est le killer de tout le monde. "
			msg_members_vivants += f"Vous pouvez donc réaliser votre mission sur qui vous voulez, et vous devez vous méfier de tous les autres joueurs... "
			msg_members_vivants += f"Pour m'informer que vous avez réalisé votre mission sur un joueur, envoyez-moi \"parano{'{ïa}'} <pseudo>\" (c'est le \"vrai\" killer de la personne que vous avez tué qui récupèrera sa mission, donc vous changerez de mission uniquement si votre \"vraie\" cible meurt). "
			msg_members_vivants += f"Si vous réalisez votre mission sur un joueur mort, vous ne serez pas au courant qu'il était déjà mort, tout se passera pour vous comme si vous veniez de le tuer (vous récupérerez d'ailleurs bien un kill)."
			msg_members_vivants += f"Vous pouvez toujours tenter de démasquer votre \"vrai\" killer. "
			msg_members_morts =  f"**[Événement quotidien : paranoïa]**\n"
			msg_members_morts += f"Aujourd'hui, tout le monde est la cible de tout le monde, et tout le monde est le killer de tout le monde. "
			msg_members_morts += f"Des joueurs vivants ignorant que vous êtes mort vont peut-être tenter de vous tuer. "
			msg_members_morts += f"Si c'est le cas, répondez juste \"oui\" quand je vous demande si l'un d'entre eux a bien réalisé sa mission (s'il a bien réalisé sa mission et s'il peut ne pas savoir que vous êtes mort, répondez \"non\" s'il a réalisé sa mission mais qu'il sait que vous êtes mort)."
			for member in self.members :
				if self.members[member]['state'] == "en vie" :
					await self.fetch_member(member).dm_channel.send(msg_members_vivants)
				elif self.members[member]['state'] == "mort" :
					await self.fetch_member(member).dm_channel.send(msg_members_morts)

		elif event == "ville fantôme" :

			# liste des joueurs en vie
			liste_joueurs_en_vie = []

			# liste des joueurs morts
			liste_joueurs_morts = []

			# liste des missions des anciennes parties
			liste_missions = []

			# on remplie les listes
			for member in self.members :
				if self.members[member]["state"] == "en vie" :
					liste_joueurs_en_vie.append(member)
				elif self.members[member]["state"] == "mort" :
					liste_joueurs_morts.append(member)
				for mission in self.missions[member] :
					if mission != "" :
						liste_missions.append(mission)

			self.events["ville fantôme"]["liste_morts"] = liste_joueurs_morts

			# copie de liste_joueurs_en_vie
			liste_joueurs_en_vie_saved = list(liste_joueurs_en_vie)

			# on donne une cible et une mission à chaque joueur mort
			for member in liste_joueurs_morts :

				# si la liste des gens mort est vide ou qu'il ne reste que l'ancienne cible, on la reset
				if liste_joueurs_en_vie_saved == [] or liste_joueurs_en_vie_saved == [self.events['ville fantôme'][member]['previous target']] :
					liste_joueurs_en_vie_saved = list(liste_joueurs_en_vie)

				# distribution de la cible parmis les vivant (cible différente de l'ancienne cible)
				target = liste_joueurs_en_vie_saved[random.randint(0,len(liste_joueurs_en_vie_saved)-1)]
				while target == self.events['ville fantôme'][member]['previous target'] :
					target = liste_joueurs_en_vie_saved[random.randint(0,len(liste_joueurs_en_vie_saved)-1)]

				# on supprime la cible distribuée de la liste des cibles disponibles					
				liste_joueurs_en_vie_saved.remove(target)

				# distribution de la mission
				mission = liste_missions[random.randint(0,len(liste_missions)-1)]

				self.events["ville fantôme"][member] = {
					"target" : target,
					"mission" : mission
				}

			# la gazette des gens morts
			msg = f"**[VILLE FANTÔME]** - :ghost::house_abandoned: [:skull:] Liste des joueurs morts au début de la ville fantôme :\n\n"
			for member in liste_joueurs_morts :
				msg += f"- {member}\n"
			msg += f"\u200B"
			self.informer(msg)
			msg = f"**[VILLE FANTÔME]** - :ghost::house_abandoned: [:dart:] Cibles reçues par les joueurs morts :\n\n"
			for member in liste_joueurs_morts :
				msg += f"- {member} ===> {self.events['ville fantôme'][member]['target']}\n"
			msg += f"\u200B"
			self.informer(msg)
			msg = f"**[VILLE FANTÔME]** - :ghost::house_abandoned: [:ballot_box_with_check:] Missions reçues par les joueurs morts :\n\n"
			for member in liste_joueurs_morts :
				msg += f"- {member} : {self.events['ville fantôme'][member]['mission'][::-1]}\n"
			msg += f"\u200B"
			self.informer(msg)

			msg_channel =  f"**[Événement quotidien : ville fantôme]**\n"
			msg_channel += f"Aujourd'hui, les morts reviennent à la vie !"
			msg_channel += f"Chaque mort se voit attribuer une cible parmis les joueurs vivants et une mission parmis les missions des anciennes parties de killer."
			msg_channel += f"Si un mort réussit à réaliser la mission qui lui a été attibuée avant la fin de la journée, sa cible meurt et il revient pour de bon dans la partie en prenant la place du joueur qu'il a tué."
			msg_channel += f"Étant donné que cela modifie fortement le cours de la partie, j'annoncerai en direct si un mort a réalisé sa mission et revient dans la partie (sans donner l'identité de ce joueur).\n"
			msg_channel += f"NB1: vous ne pouvez pas tenter de démasquer votre killer mort si vous en avez un. Le killer que vous pouvez démasquer est celui qui est vivant.\n"
			msg_channel += f"NB2: s'il y a plus de morts que de vivants au début de l'événement, plusieurs morts peuvent avoir la même cible parmis les vivants."
			msg_channel += f"Dans ce cas, si un mort réalise sa mission et prend la place de sa cible dans la partie, les autres morts ayant la même cible ne peuvent plus revenir dans la partie."
			await self.bot_channel.send(msg_channel)
			msg_morts =  f"**[Événement quotidien : ville fantôme]**\n"
			msg_morts += f"Aujourd'hui, vous allez pouvoir tenter de revenir dans la partie en tuant un joueur en vie."
			msg_morts += f"Si vous y arrivez avant minuit, vous reviendrez dans la partie en prenant la place de la personne que vous avez tué."
			msg_morts += f"Pour m'annoncer que vous avez réalisé cette mission, cela se passe de la même manière que si vous étiez en vie : envoyez-moi \"gotcha\" et je m'occupe du reste."
			msg_morts += f"Attention : si un autre mort a la même cible que vous, c'est le plus rapide de vous deux à réaliser sa mission qui reviendra à la vie donc dépêchez-vous !\n"
			msg_vivants =  f"**[Événement quotidien : ville fantôme]**\n"
			msg_vivants += f"Aujourd'hui, les morts reviennent à la vie. L'un d'entre eux vous a peut-être pour cible, méfiez-vous."
			for member in self.members :
				if self.members[member]["state"] == "en vie" :
					await self.fetch_member(member).dm_channel.send(msg_vivants)
				elif self.members[member]["state"] == "mort" :
					await self.fetch_member(member).dm_channel.send(msg_morts+f"Ta cible : {self.events['ville fantôme'][member]['target']}\nTa mission : {self.events['ville fantôme'][member]['mission'][::-1]}")

		self.write_events()

	def find_killer(self, name) :

		""" Finds a member by the name of his target
		Parameters :
			- name (str): the name of a member of the guild (ex: M1k3y#8407)
		Returns :
			- member (str or None): the name of the member having 'name' as target if such a member exists (None else)		
		"""

		for member in self.members :
			if self.members[member]["target"] == name :
				return member
		return None

	def fetch_member(self, name) :

		""" Finds a member by his name
		Parameters :
			- name (str): the name of a member of the guild (ex: M1k3y#8407)
		Returns : 
			- member (discord.Member): the corresponding discord.Member
		"""

		for member in self.bot_guild.members :
			if str(name) == f"{member.name}#{member.discriminator}" :
				return member
		return None

	def who_wrote_this_mission(self, mission) :

		""" Finds the member who invented the given mission
		Parameters :
			- mission (str) : the mission to find (written as stocked in members_file)
		Returns :
			- member (str) : the name of the member who wrote this mission
		"""

		for member in self.members :
			if self.members[member]["proposed mission"] == str(mission) :
				return member
		return None

	def sort_messages(self, messages) :
		""" Sorts a list of Messages by date
		Parameters :
			- messages (List[discord.Message]): a list of messages
		Returns :
			- messages (List[discord.Message]): the same list, sorted by date (discord.Message.created_at)
		"""
		for i in range(1, len(messages)) :

			message_i = messages[i] # message que l'on cherche à mettre à sa place dans la liste
			j = i

			while j>0 and messages[j-1].created_at > message_i.created_at :

				messages[j] = messages[j-1]
				j -= 1

			messages[j] = message_i

		return messages

	async def end_of_game(self, winners) :

		if self.vars['game_started'] :

			msg = f"======== La partie de killer est terminée ========\n\n"

			# message de félicitation du vainqueur
			if len(winners) == 1 :
				msg += f"Bravo à :medal: ***{winners[0]}*** :medal: qui remporte cette partie !\n\n"
				self.members[winners[0]]["wins"] = str(int(self.members[winners[0]]["wins"])+1)
			elif len(winners) > 1 :
				msg += f"Aucun gagnant cette fois-ci car plusieurs joueurs sont encore en vie.\n\n"

			# record de kills de la partie
			max_kills = 0
			for member in self.members :
				if self.members[member]["state"] in ["mort", "en vie"] and int(self.members[member]["kills_game"]) > max_kills :
						max_kills = int(self.members[member]["kills_game"])

			# liste des joueurs ayant atteint ce record de kills
			best_killers = []
			for member in self.members :
				if self.members[member]["state"] in ["mort", "en vie"] and int(self.members[member]["kills_game"]) == max_kills :
					best_killers.append(member)

			# message de félicitation de ces joueurs
			msg += f"Et bravo à {best_killers[0]}"
			if len(best_killers) > 2 :
				for member in best_killers[1:-1] :
					msg += f", {member}"
			if len(best_killers) > 1 :
				msg += f" et {best_killers[-1]}"
			msg += f" pour avoir réalisé le maximum de kills de cette partie ({max_kills} kill{'s' if max_kills > 1 else ''})\n\n"
			msg += f"============================================="

			await self.bot_channel.send(msg)	

			# la gazette des gens morts
			for info_msg in self.vars['gazette'] :
				await self.gazette_channel.send(info_msg)

			#===================#
			# ON REMET TOUT À 0 #
			#===================#

			for member in self.members :

				# si le membre a participé à la partie
				if self.members[member]["state"] in ["mort", "en vie"] :

					# on incrémente son nombre de parties jouées
					self.members[member]["games_played"] = str(int(self.members[member]["games_played"])+1)

					# on informe le joueur que la partie est finie
					await self.fetch_member(member).dm_channel.send(f"La partie de killer est terminée.")

				# on ajoute la mission proposée aux anciennes missions
				self.missions[member].append(self.members[member]["proposed mission"])

				self.members[member]['questioned'] = False
				self.members[member]['current_question'] = ""
				self.members[member]['other_questions'] = []

				self.members[member]["state"]            = "non-inscrit"
				self.members[member]["tags"]             = []
				self.members[member]["proposed mission"] = ""
				self.members[member]["mission to do"]    = ""
				self.members[member]["target"]           = ""
				self.members[member]["kills_game"]       = "0"

			# vars
			self.vars = {
				"day" : 0,
				"event" : "",
				"gazette": [],
				"game_started": False,
				"players_alive": [],
				"kills_count": 0,
				"clock_hours_offset": 2,
				"deaths_annouce_limit": 5
			}

			# events
			for member in self.members :
				self.events["rumeurs"][member] = ""
				self.events["killer guess"][member] = ""
				self.events["ville fantôme"][member] = {
					"target" : "",
					"mission" : ""
				}

			self.write_members()
			self.write_missions()
			self.write_events()
			self.write_vars()

			self.log(f"Partie terminée !")

		else :

			logging.error(f"Trying to stop a game that doesn't exist !")
			await self.log_channel.send(f"**/!\\/!\\/!\\ Trying to stop a game that doesn't exist ! /!\\/!\\/!\\**")

	async def kill_player(self, player, transfer_mission=True, ville_fantome=False, killer_mort=None) :

		if self.members[player]["state"] == "en vie" :

			if ville_fantome :

				# le joueur mort qui revient dans la partie
				mort = killer_mort
				Mort = self.fetch_member(mort)

				# le joueur qui meurt
				Player = self.fetch_member(player)

				# le killer du joueur qui meurt
				killer = self.find_killer(player)
				Killer = self.fetch_member(killer)

				# modifications pour le mort qui revient
				self.members[mort]["state"]         = "en vie"
				self.members[mort]["kills"]         = str(int(self.members[mort]["kills"])+1)
				self.members[mort]["kills_game"]    = str(int(self.members[mort]["kills_game"])+1)
				self.members[mort]["mission to do"] = self.members[player]["mission to do"]
				self.members[mort]["target"]        = self.members[player]["target"]

				# modifications pour le joueur qui s'est fait tué
				self.members[player]["deaths"]        = str(int(self.members[player]["deaths"])+1)
				self.members[player]["state"]         = "mort"
				self.members[player]["mission to do"] = ""
				self.members[player]["target"]        = ""

				# modifications pour le killer du joueur qui s'est fait tué
				self.members[killer]["target"] = mort

				self.vars['players_alive'].remove(player)
				self.vars['players_alive'].append(mort)

				self.write_members()
				self.write_vars()

				await Mort.dm_channel.send(f"Bravo ! Tu as réussi à réaliser ta mission et tu reviens dans la partie !\nTa mission : {self.members[mort]['mission to do'][::-1]}\nTa cible : {self.members[mort]['target']}")
				await Player.dm_channel.send(f"Tu es éliminé. Merci d'avoir joué et à bientôt dans une prochaine partie de Killer.")
				await Killer.dm_channel.send(f"Ta cible est morte.")
				await Killer.dm_channel.send(f"Nouvelle cible : {self.members[killer]['target']}")
				await Killer.dm_channel.send(f"Tu gardes ton ancienne mission ({self.members[killer]['mission to do'][::-1]}). Uniquement la cible de cette mission change.")
				await self.bot_channel.send(f"**[VILLE FANTÔME]** - Attention : un joueur mort a réalisé sa mission et revient dans la partie.")

			else :

				killer = self.find_killer(player) # str
				Killer = self.fetch_member(killer) # discord.Member

				# on enregistre la cible du mort pour qu'il ne puisse pas tomber dessus lors de la ville fantôme
				self.events['ville fantôme'][player]['previous target'] = self.members[player]['target']

				# modifications killer
				if transfer_mission :
					self.members[killer]["mission to do"] = self.members[player]["mission to do"]
				self.members[killer]["target"] = self.members[player]["target"]

				# modification joueur mort
				self.members[player]["deaths"]        = str(int(self.members[player]["deaths"])+1)
				self.members[player]["state"]         = "mort"
				self.members[player]["mission to do"] = ""
				self.members[player]["target"]        = ""

				# on supprime le joueur mort de la liste des joueurs en vie
				self.vars['players_alive'].remove(player)
				self.vars['kills_count'] += 1

				self.write_members()
				self.write_events()
				self.write_vars()

				# annoncer sa mort à la personne morte
				await self.fetch_member(player).dm_channel.send(f"Tu es éliminé. Merci d'avoir joué et à bientôt dans une prochaine partie de Killer.")

				# annoncer la mort de sa cible au killer
				if len(self.vars['players_alive']) > 1 :
					await Killer.dm_channel.send(f"Ta cible est morte.")
					await Killer.dm_channel.send(f"Nouvelle cible : {self.members[killer]['target']}")
					if transfer_mission :
						await Killer.dm_channel.send(f"Nouvelle mission (gentiment inventée par {self.who_wrote_this_mission(self.members[killer]['mission to do'])}) : {self.members[killer]['mission to do'][::-1]}")
					else : 
						await Killer.dm_channel.send(f"Tu gardes ton ancienne mission ({self.members[killer]['mission to do'][::-1]}). Uniquement la cible de cette mission change.")

			self.log(f"{player} est mort ! transfer_mission: {transfer_mission} / ville_fantome: {ville_fantome} / killer_mort: {killer_mort}")

		else :

			logging.error(f"Trying to kill a member who's not alive !")
			await self.log_channel.send(f"**/!\\/!\\/!\\ Trying to kill a member who's not alive ! /!\\/!\\/!\\**")

	#=================================#
	# SENDING RANKINGS IN BOT CHANNEL #
	#=================================#

	async def kill_ranking(self) :
		
		kill_list = []
		for member in self.members :
			if int(self.members[member]["kills"]) > 0 :
				kill_list.append((member,int(self.members[member]["kills"])))

		for i in range(1,len(kill_list)) :
			x = kill_list[i]
			j = i
			while j>0 and kill_list[j-1][1] < x[1] :
				kill_list[j] = kill_list[j-1]
				j -= 1
			kill_list[j] = x

		kills_ranking_msg = f"=============== Meilleurs killers ===============\n\n"
		for i in range(len(kill_list)) :
			if i == 0 :
				kills_ranking_msg += f":first_place: : {kill_list[0][0]} ({kill_list[0][1]} kill{'s' if kill_list[0][1]>1 else ''})\n"
			elif i == 1 :
				kills_ranking_msg += f":second_place: : {kill_list[1][0]} ({kill_list[1][1]} kill{'s' if kill_list[1][1]>1 else ''})\n"
			elif i == 2 :
				kills_ranking_msg += f":third_place: : {kill_list[2][0]} ({kill_list[2][1]} kill{'s' if kill_list[2][1]>1 else ''})\n"
			else :
				kills_ranking_msg += f"{i+1}eme : {kill_list[i][0]} ({kill_list[i][1]} kill{'s' if kill_list[i][1]>1 else ''})\n"
		kills_ranking_msg += f"\n============================================="
		await self.bot_channel.send(kills_ranking_msg)

	async def wins_ranking(self) :

		wins_list = []
		for member in self.members :
			if int(self.members[member]["wins"]) > 0 :
				wins_list.append((member,int(self.members[member]["wins"])))

		for i in range(1,len(wins_list)) :
			x = wins_list[i]
			j = i
			while j>0 and wins_list[j-1][1] < x[1] :
				wins_list[j] = wins_list[j-1]
				j -= 1
			wins_list[j] = x

		wins_ranking_msg = f"=========== Classement par victoires ===========\n\n"
		for i in range(len(wins_list)) :
			if i == 0 :
				wins_ranking_msg += f":first_place: : {wins_list[0][0]} ({wins_list[0][1]} victoire{'s' if wins_list[0][1]>1 else ''})\n"
			elif i == 1 :
				wins_ranking_msg += f":second_place: : {wins_list[1][0]} ({wins_list[1][1]} victoire{'s' if wins_list[1][1]>1 else ''})\n"
			elif i == 2 :
				wins_ranking_msg += f":third_place: : {wins_list[2][0]} ({wins_list[2][1]} victoire{'s' if wins_list[2][1]>1 else ''})\n"
			else :
				wins_ranking_msg += f"{i+1}eme : {wins_list[i][0]} ({wins_list[i][1]} victoire{'s' if wins_list[i][1]>1 else ''})\n"
		wins_ranking_msg += f"\n============================================="
		await self.bot_channel.send(wins_ranking_msg)

	async def killrate_ranking(self) :

		killrate_list = []
		for member in self.members :
			if int(self.members[member]["wins"]) + int(self.members[member]["deaths"]) > 0 :
				killrate = int(self.members[member]["kills"])/(int(self.members[member]["wins"]) + int(self.members[member]["deaths"]))
				killrate_list.append((member,killrate))

		for i in range(1,len(killrate_list)) :
			x = killrate_list[i]
			j = i
			while j>0 and killrate_list[j-1][1] < x[1] :
				killrate_list[j] = killrate_list[j-1]
				j -= 1
			killrate_list[j] = x

		killrate_ranking_msg = f"============ Classement par killrate ============\n\n"
		for i in range(len(killrate_list)) :
			if i == 0 :
				killrate_ranking_msg += f":first_place: : {killrate_list[0][0]} ({killrate_list[0][1]:.3f})\n"
			elif i == 1 :
				killrate_ranking_msg += f":second_place: : {killrate_list[1][0]} ({killrate_list[1][1]:.3f})\n"
			elif i == 2 :
				killrate_ranking_msg += f":third_place: : {killrate_list[2][0]} ({killrate_list[2][1]:.3f})\n"
			else :
				killrate_ranking_msg += f"{i+1}eme : {killrate_list[i][0]} ({killrate_list[i][1]:.3f})\n"
		killrate_ranking_msg += f"\n============================================="
		await self.bot_channel.send(killrate_ranking_msg)

	async def winrate_ranking(self) :
		
		winrate_list = []
		for member in self.members :
			if int(self.members[member]["wins"]) + int(self.members[member]["deaths"]) > 0 :
				winrate = int(self.members[member]["wins"])/(int(self.members[member]["wins"]) + int(self.members[member]["deaths"]))
				winrate_list.append((member,winrate))

		for i in range(1,len(winrate_list)) :
			x = winrate_list[i]
			j = i
			while j>0 and winrate_list[j-1][1] < x[1] :
				winrate_list[j] = winrate_list[j-1]
				j -= 1
			winrate_list[j] = x

		killrate_ranking_msg = f"============ Classement par winrate ===========\n\n"
		for i in range(len(winrate_list)) :
			if i == 0 :
				killrate_ranking_msg += f":first_place: : {winrate_list[0][0]} ({winrate_list[0][1]:.3f})\n"
			elif i == 1 :
				killrate_ranking_msg += f":second_place: : {winrate_list[1][0]} ({winrate_list[1][1]:.3f})\n"
			elif i == 2 :
				killrate_ranking_msg += f":third_place: : {winrate_list[2][0]} ({winrate_list[2][1]:.3f})\n"
			else :
				killrate_ranking_msg += f"{i+1}eme : {winrate_list[i][0]} ({winrate_list[i][1]:.3f})\n"
		killrate_ranking_msg += f"\n============================================="
		await self.bot_channel.send(killrate_ranking_msg)

	#=======================================#
	# PROCESS A MESSAGE RECEIVED BY THE BOT #
	#=======================================#

	async def process_msg(self, message): 

		# on vérifie que le message ne vient pas du bot
		if message.author != self.user and f"{message.author.name}#{message.author.discriminator}" in self.members :

			# channel de messages privés avec l'auteur du message
			dm_channel = message.author.dm_channel

			# nom de l'auteur du message (<pseudo>#<id>)
			author_name = f"{message.author.name}#{message.author.discriminator}"

			# contenu de self.members pour ce membre
			msg_author = self.members[author_name]

			# si le salon de message privé n'existe pas, on le crée
			if dm_channel == None :
				dm_channel = await message.author.create_dm()

			# si le message reçu est un message privé
			if message.channel == dm_channel :

				self.members[author_name]["last_msg_id"] = str(message.id)
				self.write_members()

				if self.members[author_name]["questioned"] and message.content.lower() not in ["oui", "non"] :
					await dm_channel.send(f"Répond d'abord à ma question précédente ! :rage:")
					return 0

				# si le message vient du propriétaire du bot
				if message.author.id == bot_owner_id :

					#===============================#
					# DÉMARRER UNE PARTIE DE KILLER #
					#===============================#

					if re.match(start_game_regexp, message.content) :
						
						if not(self.vars['game_started']) :

							player_list = []
							player_count = 0

							# on compte les joueurs inscrits
							for member in self.members :
								if self.members[member]["state"] == "inscrit" :
									player_list.append(member)
									player_count += 1

							# s'ils n'y en a pas assez, on ne démarre pas la partie
							if player_count < 4 :
								await dm_channel.send(f"La partie n'a pas pu commencer, il n'y a pas assez de joueurs inscrits")

							# début de la partie
							else :

								self.vars['day'] = 1
								self.vars['game_started'] = True
								self.vars['players_alive'] = player_list

								self.events["ville fantôme"]["active"] = True

								for member in player_list :
									self.members[member]["state"] = "en vie"
									self.members[member]["kills_game"] = "0"

								# annonce du début de la partie dans le channel du bot
								res = f"======== La partie de killer a commencé ========\n\n"
								res += f"Les participants sont :\n"
								for member in player_list :
									res += f"- {member}\n"
								res +=f"\n============================================"
								await self.bot_channel.send(res)

								# distribution des missions (on peut tomber sur sa propre mission)
								saved_player_list = list(player_list)
								random.shuffle(player_list)
								for i in range(player_count) :
									self.members[player_list[i]]["mission to do"] = self.members[saved_player_list[i]]["proposed mission"]

								# distribution des cibles (on ne peut pas tomber sur la cible ayant inventé notre mission)
								saved_player_list2 = list(player_list)
								ok = False
								while not(ok) :
									random.shuffle(player_list)
									ok = True
									for i in range(player_count) : 
										if player_list[(i+1)%player_count] == saved_player_list[saved_player_list2.index(player_list[i])] :
											ok = False
								for i in range(player_count) :
									self.members[player_list[i]]["target"] = player_list[(i+1)%player_count]
								self.write_members()

								self.events['ville fantôme']['active'] = False
								self.events['paranoïa']['active'] = False

								# choix de l'événement du premier jour
								self.vars['event'] = self.choose_event()

								# message d'information de la gazette des gens morts
								self.vars['gazette'] = [f":newspaper: **=======[La gazette des gens morts]=======** :newspaper:\n\u200B", f":checkered_flag: **[Début de la partie]**\n\u200B"]

								info_msg = ":memo: __Inscriptions__ :\n\n"
								for member in self.members :
									if self.members[member]["state"] == "en vie" :
										info_msg += f"- {member} a inventé la mission suivante : {self.members[member]['proposed mission'][::-1]}\n"
								info_msg += "\n\u200B"
								self.vars['gazette'].append(info_msg)

								info_msg = ":ballot_box_with_check: __Missions reçues__ :\n\n"
								for member in self.members :
									if self.members[member]["state"] == "en vie" :
										info_msg += f"- {member} a reçu la mission suivante : {self.members[member]['mission to do'][::-1]}\n"
								info_msg += "\n\u200B"
								self.vars['gazette'].append(info_msg)
								
								info_msg = ":dart: __Cibles reçues__ :\n\n"
								for member in self.members :
									if self.members[member]["state"] == "en vie" :
										info_msg += f"- {member} ===> {self.members[member]['target']}\n"
								info_msg += "\n\u200B"
								self.vars['gazette'].append(info_msg)

								self.vars['gazette'].append("**[Déroulement de la partie]**\n\u200B")
								self.vars['gazette'].append("#================ JOUR :one: ================#\n\u200B")
								self.vars['gazette'].append(f"__Événement du jour__ : {self.vars['event']}\n\u200B")

								# annonce des missions et des cibles en messages privés
								for member in player_list :
									Member = self.fetch_member(member)
									await Member.dm_channel.send(f"**[Début de la partie]**")
									await Member.dm_channel.send(f"{self.who_wrote_this_mission(self.members[member]['mission to do'])} a inventé cette mission pour toi : {self.members[member]['mission to do'][::-1]}")
									await Member.dm_channel.send(f"Ta cible : {self.members[member]['target']}")
									await Member.dm_channel.send(f"**[NOUVEAUTÉ]** - Vous pouvez désormais envoyer un message à votre killer une fois par jour en m'envoyant \"message killer : <message>\".")
									await Member.dm_channel.send(f"**[NOUVEAUTÉ]** - Lors de l'événement \"killer guess\", si un joueur me donne la véritable identité de son killer, j'en informerai son killer.")

								await self.process_event()
								self.write_events()
								self.write_vars()

						else :

							await dm_channel.send(f"La partie a déjà commencé")

					#==============================#
					# STOPPER UNE PARTIE DE KILLER #
					#==============================#

					elif re.match(stop_game_regexp, message.content) :

						if self.vars['game_started'] :
						
							await self.end_of_game(winners = self.vars['players_alive'])
							await dm_channel.send(f"C'est bon, j'ai mis fin à la partie")

						else :

							await dm_channel.send(f"Aucune partie n'est actuellement en cours")


					#=========================================================#
					# ENVOYER UNE COURTE PRÉSENTATION DU BOT DANS SON CHANNEL #
					#=========================================================#

					elif re.match(r".*[Pp]résentation.*", message.content) :

						await self.bot_channel.send(rules_msg)

					#======================#
					# CLASSEMENT PAR KILLS #
					#======================#

					elif re.match(r".*[Cc]lassement kills.*", message.content) :

						await self.kill_ranking()

					#==========================#
					# CLASSEMENT PAR VICTOIRES #
					#==========================#

					elif re.match(r".*[Cc]lassement wins.*", message.content) :

						await self.wins_ranking()

					#=========================#
					# CLASSEMENT PAR KILLRATE #
					#=========================#

					elif re.match(r".*[Cc]lassement killrate.*", message.content) :

						await self.killrate_ranking()

					#========================#
					# CLASSEMENT PAR WINRATE #
					#========================#

					elif re.match(r".*[Cc]lassement winrate.*", message.content) :

						await self.winrate_ranking()

					#======================#
					# AFFICHER LES MEMBRES #
					#======================#

					elif re.match(r".*[Aa]ffiche les membres.*", message.content) :

						res = f""
						if self.vars['game_started'] :

							for member in self.members :
								res += f"- {member}\n"

						else :

							for member in self.members :
								res += f"- {member} ({self.members[member]['state']})\n"

						await self.log_channel.send(res)

					#=======================#
					# DÉMARRER UN ÉVÉNEMENT #
					#=======================#

					elif re.match(r"event : (.*)", message.content.lower()) :
						match = re.match(r"[Ee][Vv][Ee][Nn][Tt] : (.*)", message.content)

						self.vars["event"] = match.group(1)
						self.write_vars()

						await self.process_event()

					#=====================#
					# DUMP CIRCLE (DEBUG) #
					#=====================#

					#elif re.match(r"circle", message.content.lower()) :

					#	await dm_channel.send(self.dump_circle(self.vars['players_alive']))

					#=================#
					# ANNONCE (DEBUG) #
					#=================#

					elif re.match(r".*annonce.*", message.content) :

						await self.annonce()

					#====================#
					# ÉTEINDRE KILLERBOT #
					#====================#

					elif re.match(r".*KILL KILLERBOT.*", message.content) :

						sys.exit()

				#===================================#
				# S'INSCRIRE À UNE PARTIE DE KILLER #
				#===================================#

				# Mission : <une mission>
				if re.match(r"[Mm]ission : (.*)", message.content) :
					match = re.match(r"[Mm]ission : (.*)", message.content)

					if not(self.vars['game_started']) :

						if author_name in self.members :

							if self.members[author_name]["state"] == "non-inscrit" :
								self.members[author_name]["state"] = "inscrit"
								self.members[author_name]["proposed mission"] = match.group(1)[::-1]
								await dm_channel.send("C'est noté, tu est inscrit(e) et ta mission a été enregistrée")
								await self.log_channel.send(f"{author_name} vient de s'inscrire.")

							elif self.members[author_name]["state"] == "inscrit" :
								self.members[author_name]["proposed mission"] = match.group(1)[::-1]
								await dm_channel.send("C'est noté, ta mission a été remplacée")

							self.write_members()

						else :

							await dm_channel.send(f"Tu ne peux pas t'inscrire car tu ne fais pas partie du serveur")

					else :

						await dm_channel.send(f"Tu ne peux pas t'inscrire, le partie a déjà commencé")

				#=======================================#
				# SE DÉSINSCRIRE D'UNE PARTIE DE KILLER #
				#=======================================#

				# Je ne veux plus jouer
				elif re.match(unregistration_regexp, message.content) :
					match = re.match(unregistration_regexp, message.content)

					if not(self.vars['game_started']) :

						if author_name in self.members :

							if self.members[author_name]["state"] == "non-inscrit" :
								await dm_channel.send(f"Tu n'es pas inscrit(e) à la prochaine partie")

							elif self.members[author_name]["state"] == "inscrit" :
								self.members[author_name]["state"] = "non-inscrit"
								self.members[author_name]["proposed mission"] = ""
								await dm_channel.send(f"C'est noté ! Tu n'es plus inscrit(e) à la prochaine partie.")
								await self.log_channel.send(f"{author_name} vient de se désinscrire.")

							self.write_members()

						else :

							await dm_channel.send(f"Tu ne peux pas te désinscrire car tu ne fais pas partie du serveur")

					else :

						await dm_channel.send(f"Tu ne peux pas te désinscrire, la partie a déjà commencé")

				#============================================#
				# TENTER DE DEVINER L'IDENTITÉ DE SON KILLER #
				#============================================#

				# Mon killer est <nom du killer>
				elif re.match(killer_found_regexp, message.content) :
					match = re.match(killer_found_regexp, message.content)

					if self.vars['game_started'] :

						target = self.members[author_name]["target"]
						Target = self.fetch_member(target)

						killer = self.find_killer(author_name)
						Killer = self.fetch_member(killer)

						killer_killer = self.find_killer(killer)
						Killer_Killer = self.fetch_member(killer_killer)

						gotcha = False
						for member in self.members :
							if "gotcha ?" in [self.members[member]["current_question"]]+self.members[member]["other_questions"] :
								gotcha = True

						if not(gotcha) :

							if match.group(1) in self.members :

								if match.group(1) == str(killer) :
									await dm_channel.send(f"Bravo ! Tu as trouvé l'identité de ton killer ! Il meurt et sa mission est donnée à son propre killer.")
									await self.fetch_member(killer).dm_channel.send(f"Ta cible a deviné ton identité.")
									self.members[author_name]["killers found"] = str(int(self.members[author_name]["killers found"])+1)
									self.members[match.group(1)]["get found"] = str(int(self.members[match.group(1)]["get found"])+1)
									await self.kill_player(match.group(1), transfer_mission=False)

									# la gazette des gens morts
									msg = f"**[KILLER]** - {author_name} a trouvé l'identité de son killer ({killer}). "
									if len(self.vars['players_alive']) > 1 :
										msg += f"Donc {killer} meurt et {killer_killer} recupère sa cible (mais pas sa mission).\nNouvelle cible de {killer_killer} : {author_name}\nNouvelle mission de {killer_killer} : {self.members[killer_killer]['mission to do'][::-1]}\n\u200B"
									else :
										msg += f"Donc {killer} meurt et {author_name} remporte la partie."
									await self.informer(msg)						

								else :
									await dm_channel.send(f"Malheureusement, {match.group(1)} n'est pas ton killer... Tu meurs donc et ton killer récupère ta mission")
									self.members[author_name]["wrong killer guess"] = str(int(self.members[author_name]["wrong killer guess"])+1)
									self.members[match.group(1)]["targets abused"] = str(int(self.members[match.group(1)]["targets abused"])+1)
									await self.kill_player(author_name)

									# la gazette des gens morts
									msg = f"**[KILLER]** - {author_name} a tenté de trouver l'identité de son killer ({killer}) mais s'est trompé(e) et a voté pour {match.group(1)}. "
									if len(self.vars['players_alive']) > 1 :
										msg += f"Donc {author_name} meurt et {killer} récupère sa cible et sa mission.\nNouvelle cible de {killer} : {target}.\nNouvelle mission de {killer} : {self.members[killer]['mission to do'][::-1]}\n\u200B"
									else :
										msg += f"Donc {author_name} meurt et {killer} remporte la partie."
									await self.informer(msg)

								self.write_members()

								if len(self.vars['players_alive']) <= 1 :
									await self.end_of_game(winners=self.vars['players_alive'])

							else :

								await dm_channel.send(f"Je ne connais pas le membre {match.group(1)}, es-tu sûr(e) de l'avoir correctement écris ? N'oublie pas d'écrire son identifiant (par exemple, pour Robin il faut écrire M1k3y#8704 et non M1k3y)")

						else :

							await dm_channel.send(f"Tu ne peux pas tenter de démasquer ton killer pour le moment car j'attend la confirmation de la mort d'un joueur de la partie. Retente un peu plus tard")

					else :

						await dm_channel.send(f"Aucune partie de killer n'est actuellement en cours")

				#=============================#
				# ANNONCER AU BOT QU'ON A TUÉ #
				#=============================#

				elif re.match(r"[Gg]otcha", message.content.lower()) :

					if self.vars['game_started'] :

						if self.vars['event'] != "paranoïa" :

							# le killer en vie a tué sa cible
							if self.members[author_name]["state"] == "en vie" :

								target = self.members[author_name]["target"]
								Target = self.fetch_member(target)

								if "gotcha ?" not in [self.members[target]["current_question"]]+self.members[target]["other_questions"] :

									# on envoie la question à la cible (en forçant son envoi même si une autre question est en attente de réponse)
									self.members[target]["other_questions"] = ["gotcha ?"] + self.members[target]["other_questions"]
									self.members[target]["questioned"] = False
									await self.send_next_question(target)

									# on informe l'auteur qu'on a demandé confirmation à sa cible
									await dm_channel.send(f"J'ai demandé confirmation à ta cible, tu recevras une nouvelle mission si elle confirme que tu as réalisé ta mission")

								else :

									await dm_channel.send(f"J'ai déjà demandé confirmation à ta cible, attend qu'elle réponde")

							# un killer mort a tué sa cible lors de l'événement "ville fantôme"
							elif self.vars["event"] == "ville fantôme" and author_name in self.events["ville fantôme"]["liste_morts"] and self.members[self.events["ville fantôme"][author_name]["target"]]["state"] == "en vie" :

								target = self.events["ville fantôme"][author_name]["target"]
								Target = self.fetch_member(target)

								if f"gotcha ville fantôme {author_name} ?" not in [self.members[target]["current_question"]]+self.members[target]["other_questions"] :

									if self.members[target]["current_question"] == "gotcha ?" :

										self.members[target]["other_questions"] = [f"gotcha ville fantôme {author_name} ?"] + self.members[target]["other_questions"]
										await self.send_next_question(target)

									elif len(self.members[target]["other_questions"]) > 0 and self.members[target]["other_questions"][0] == "gotcha ?" :

										self.members[target]["other_questions"] = ["gotcha ?", f"gotcha ville fantôme {author_name} ?"] + self.members[target]["other_questions"][1:]
										self.members[target]["questioned"] = False
										await self.send_next_question(target)

									else :

										self.members[target]["other_questions"] = [f"gotcha ville fantôme {author_name} ?"] + self.members[target]["other_questions"]
										self.members[target]["questioned"] = False
										await self.send_next_question(target)

									await dm_channel.send(f"J'ai demandé confirmation à ta cible, tu recevras une nouvelle mission si elle confirme que tu as réalisé ta mission")

								else :

									await dm_channel.send(f"J'ai déjà demandé confirmation à ta cible, attend qu'elle réponde")

							else :

								await dm_channel.send(f"Tu ne peux pas tuer")

						else :

							await dm_channel.send(f"L'événement du jour est \"paranoïa\". Si tu as réalisé ta mission, tu dois m'envoyer \"parano{'{ïa}'} <pseudo>\" (même si tu as réalisé ta mission sur ta vraie cible).")

					else :

						await dm_channel.send(f"Aucune partie en cours")

					self.write_members()

				#==================================================#
				# ANNONCER AU BOT QU'ON A TUÉ (ÉVÉNEMENT PARANOÏA) #
				#==================================================#

				elif re.match(r"[Pp]arano(ïa)? (.*)", message.content) :

					if self.vars['game_started'] :

						if self.vars['event'] == "paranoïa" :

							pseudo = re.match(r"[Pp]arano(ïa)? (.*)", message.content).group(2)

							if pseudo in self.members :

								target = pseudo
								Target = self.fetch_member(target)

								if f"gotcha paranoïa {author_name} ?" not in [self.members[target]["current_question"]]+self.members[target]["other_questions"] :

									if self.members[target]["current_question"] == "gotcha ?" :

										self.members[target]["other_questions"] = [f"gotcha paranoïa {author_name} ?"] + self.members[target]["other_questions"]
										await self.send_next_question(target)

									elif len(self.members[target]["other_questions"]) > 0 and self.members[target]["other_questions"][0] == "gotcha ?" :

										self.members[target]["other_questions"] = ["gotcha ?", f"gotcha paranoïa {author_name} ?"] + self.members[target]["other_questions"][1:]
										self.members[target]["questioned"] = False
										await self.send_next_question(target)

									else :

										self.members[target]["other_questions"] = [f"gotcha paranoïa {author_name} ?"] + self.members[target]["other_questions"]
										self.members[target]["questioned"] = False
										await self.send_next_question(target)

									await dm_channel.send(f"J'ai demandé confirmation à {pseudo}")

								else :

									await dm_channel.send(f"J'ai déjà demandé confirmation à ta cible, attend qu'elle réponde")

							else :

								await dm_channel.send(f"Je ne connais pas le membre {match.group(1)}, es-tu sûr(e) de l'avoir correctement écris ? N'oublie pas d'écrire son identifiant (par exemple, pour Robin il faut écrire M1k3y#8704 et non M1k3y)")

						else :

							await dm_channel.send(f"L'événement du jour n'est pas \"paranoïa\". Envoie-moi uniquement \"gotcha\" si tu as réalisé ta mission.")

					else :

						await dm_channel.send(f"Aucune partie en cours")

				#=================================#
				# ENVOYER UN MESSAGE À SON KILLER #
				#=================================#

				elif re.match(r"[Mm]essage killer : (.*)", message.content) :

					if self.vars['game_started'] :

						if not(self.members[author_name]['msg_sent']) :

							match = re.match(r"[Mm]essage killer : (.*)", message.content)
							killer = self.find_killer(author_name)
							Killer = self.fetch_member(killer)
							await Killer.dm_channel.send(f"Ta cible m'a demandé de te transmettre le message suivant : {match.group(1)}")
							await dm_channel.send(f"Voilà, j'ai envoyé ton message à ton killer. Tu pourras à nouveau envoyer un message à ton killer demain.")
							self.members[author_name]['msg_sent'] = True
							self.write_members()

						else :

							await dm_channel.send(f"Tu as déjà envoyé un message à ton killer aujourd'hui")

					else :

						await dm_channel.send(f"Aucune partie en cours")

				#===============================#
				# RÉPONDRE "OUI" À UNE QUESTION # gotcha? info?
				#===============================#

				elif message.content.lower() == "oui" :

					if self.vars['game_started'] :

						# l'auteur du message confirme sa mort (donc meurt)
						if self.members[author_name]["current_question"] == "gotcha ?" :

							target = self.members[author_name]["target"]
							Target = self.fetch_member(target)
							self.log(f"target : {target}")

							killer = self.find_killer(author_name)
							Killer = self.fetch_member(killer)
							self.log(f"killer : {killer}")

							old_mission = self.members[killer]["mission to do"]
							new_mission = self.members[author_name]["mission to do"]

							# on incrémente les kills du killer
							self.members[killer]["kills"] = str(int(self.members[killer]["kills"])+1)
							self.members[killer]["kills_game"] = str(int(self.members[killer]["kills_game"])+1)

							# on tue l'auteur du message
							await self.kill_player(author_name)

							# la gazette des gens morts
							msg = f"**[KILLER]** - {killer} a tué {author_name} en réalisant sa mission (qui était \"{old_mission[::-1]}\"). "
							if len(self.vars['players_alive']) > 1 :
								msg += f"Donc {author_name} meurt et {killer} récupère sa cible et sa mission.\nNouvelle cible de {killer} : {target}\nNouvelle mission de {killer} : {new_mission[::-1]}\n\u200B"
							else :
								msg += f"Donc {author_name} meurt et {killer} remporte la partie."
							await self.informer(msg)

							# s'il ne reste qu'un joueur en vie, on met fin à la partie
							if len(self.vars['players_alive']) <= 1 :
								await self.end_of_game(winners = self.vars['players_alive'])

						elif re.match(r"gotcha ville fantôme ([^ ].*[^ ]) \?", self.members[author_name]["current_question"]) :
							match = re.match(r"gotcha ville fantôme ([^ ].*[^ ]) \?", self.members[author_name]["current_question"])

							# la gazette des gens morts
							msg =  f"**[VILLE FANTÔME]** - :ghost::house_abandoned: Le joueur {match.group(1)} a réussi la mission qui lui a été donnée dans le cadre de l'événement \"ville fantôme\"."
							msg += f"Il revient donc à la vie et prend la place de {author_name}.\n"
							msg += f"Sa nouvelle mission : {self.members[author_name]['mission to do'][::-1]}\n"
							msg += f"Sa nouvelle cible : {self.members[author_name]['target']}\n\u200B"
							await self.informer(msg)

							await self.kill_player(author_name, ville_fantome=True, killer_mort=match.group(1))

						elif re.match(r"gotcha paranoïa ([^ ].*[^ ]) \?", self.members[author_name]["current_question"]) :
							match = re.match(r"gotcha paranoïa ([^ ].*[^ ]) \?", self.members[author_name]["current_question"])

							# la gazette des gens morts
							msg = f"**[PARANOÏA]** - Le joueur {match.group(1)} a tué {author_name} en réalisant sa mission. "
							if self.members[author_name]['state'] == "en vie" and len(self.vars['players_alive']) > 2 :
								msg += f"Donc {author_name} meurt et {self.find_killer(author_name)} récupère sa cible et sa mission.\n"
								msg += f"Nouvelle mission de {self.find_killer(author_name)} : {self.members[author_name]['mission to do'][::-1]}\n"
								msg += f"Nouvelle cible de {self.find_killer(author_name)} : {self.members[author_name]['target']}\n\u200B"
							elif self.members[author_name]['state'] == "en vie" and len(self.vars['players_alive']) <= 2 :
								msg += f"Donc {author_name} meurt et {match.group(1)} remporte la partie."
							elif self.members[author_name]['state'] == "mort" :
								msg += f"Comme {author_name} était déjà mort(e), il ne se passe rien de spécial. {match.group(1)} récupère tout de même un kill."
							await self.informer(msg)

							# on incrémente les kills du killer
							self.members[match.group(1)]["kills"] = str(int(self.members[match.group(1)]["kills"])+1)
							self.members[match.group(1)]["kills_game"] = str(int(self.members[match.group(1)]["kills_game"])+1)

							await self.fetch_member(match.group(1)).dm_channel.send(f"{author_name} a confirmé que tu as réalisé ta mission")

							if self.members[author_name]['state'] == "en vie" :
								await self.kill_player(author_name)

							# s'il ne reste qu'un joueur en vie, on met fin à la partie
							if len(self.vars['players_alive']) <= 1 :
								await self.end_of_game(winners = self.vars['players_alive'])		

						elif self.members[author_name]["current_question"] == "info message ?" :

							await self.send_info_msg(author_name)

						elif self.members[author_name]["current_question"] == "get informed ?" :

							if "info" not in self.members[author_name]["tags"] :
								self.members[author_name]["tags"].append("info")
							await dm_channel.send(f"Très bien, tu seras informé(e) en avant première lorsque quelque chose se passera dans la partie de killer (fais bien attention à ne jamais divulguer des informations sur la partie aux joueurs en vie)")

						else :

							await dm_channel.send(f"Comment ça \"{message.content}\" ? J'ai même pas posé de question")

					else :

						await dm_channel.send(f"Aucune partie en cours")

					self.members[author_name]["questioned"] = False
					await self.send_next_question(author_name)
					self.write_members()

				#===============================#
				# RÉPONDRE "NON" À UNE QUESTION # gotcha? info?
				#===============================#

				elif message.content.lower() == "non" :

					if self.vars['game_started'] :

						# l'auteur nie avoir été tué par son killer
						if self.members[author_name]["current_question"] == "gotcha ?" :

							killer = self.find_killer(author_name)
							Killer = self.fetch_member(killer)

							await dm_channel.send(f"Ah bon ? Tu devrais en discuter avec {killer}. Il/elle ne semble pas être du même avis.")
							await Killer.dm_channel.send(f"Ta cible n'est pas d'accord avec toi sur le fait que tu aies réussi ta mission. Tu devrais aller lui parler, peut-être qu'elle a oublié le moment où tu l'as fais.")

						elif re.match(r"gotcha ville fantôme ([^ ].*[^ ]) ?", self.members[author_name]["current_question"]) :
							match = re.match(r"gotcha ville fantôme ([^ ].*[^ ]) ?", self.members[author_name]["current_question"])

							await dm_channel.send(f"Ah bon ? Tu devrais en discuter avec {match.group(1)}. Il/elle ne semble pas être du même avis.")
							await self.fetch_member(match.group(1)).dm_channel.send(f"Ta cible n'est pas d'accord avec toi sur le fait que tu aies réussi ta mission. Tu devrais aller lui parler, peut-être qu'elle a oublié le moment où tu l'as fais.")

						elif re.match(r"gotcha paranoïa ([^ ].*[^ ]) \?", self.members[author_name]["current_question"]) :
							match = re.match(r"gotcha paranoïa ([^ ].*[^ ]) \?", self.members[author_name]["current_question"])

							await dm_channel.send(f"Ah bon ? Tu devrais en discuter avec {match.group(1)}. Il/elle ne semble pas être du même avis.")
							await self.fetch_member(match.group(1)).dm_channel.send(f"{author_name} n'est pas d'accord avec toi sur le fait que tu aies réussi ta mission. Tu devrais aller lui parler, peut-être qu'elle a oublié le moment où tu l'as fais.")

						elif self.members[author_name]["current_question"] == "info message ?" :

							await dm_channel.send(f"D'accord, je ne t'envoie pas la gazette des gens morts. Si tu changes d'avis, tu peux me la redemander en m'envoyant \"gazette\"")

						elif self.members[author_name]["current_question"] == "get informed ?" :

							if "info" in self.members[author_name]["tags"] :
								self.members[author_name]["tags"].remove("info")
							await dm_channel.send(f"D'accord, tu ne sera pas informé(e) des prochains événements de la partie de killer. Si tu changes d'avis, envoie-moi \"gazette\"")

						else :

							await dm_channel.send(f"Comment ça \"{message.content}\" ? J'ai même pas posé de question")

					else :

						await dm_channel.send(f"Aucune partie en cours")

					self.members[author_name]["questioned"] = False
					await self.send_next_question(author_name)
					self.write_members()

				#==============#
				# INFORMATIONS #
				#==============#

				elif re.match(r"[Gg]azette", message.content.lower()) :

					if self.vars['game_started'] :

						# si (le joueur est non-inscrit) OU (le joueur est mort ET la ville fantôme est passée ET la ville fantôme est finie)
						if (self.members[author_name]["state"] == "non-inscrit") or (self.members[author_name]["state"] == "mort" and not(self.events["ville fantôme"]["active"]) and self.vars["event"] != "ville fantôme") :

							self.members[author_name]["other_questions"].append(f"info message ?")
							self.members[author_name]["other_questions"].append(f"get informed ?")
							await self.send_next_question(author_name)

						else :

							await dm_channel.send(f"Je détecte une tentative de triche... N'essairais-tu pas d'obtenir des informations auxquelles tu n'es pas censé avoir accès ? :thinking:")

					else :

						await dm_channel.send(f"Je ne peux pas te tenir au courant du déroulement de la partie en cours, aucune partie n'est actuellement en cours")

					self.write_members()

				#=========#
				# RUMEURS #
				#=========#

				elif re.match(r"[Rr]umeur : .*", message.content.lower()) :
					match = re.match(r"[Rr][Uu][Mm][Ee][Uu][Rr] : (.*)", message.content)

					if self.vars['game_started'] :

						if self.vars["event"] == "rumeurs" :

							if self.members[author_name]["state"] in ["mort", "en vie"] :

								if (message.created_at.hour+2)%24<12 :

									self.events["rumeurs"][author_name] = match.group(1)
									await dm_channel.send("C'est noté ! Ta rumeur a été enregistrée")
									await self.informer(f"**[RUMEURS]** - :speaking_head: Le joueur {author_name} veut répandre la rumeur suivante : {match.group(1)}\n\u200B")
									self.write_events()

								else :

									await dm_channel.send(f"Malheureusement, tu m'envoies cette rumeur trop tard. La prochaine fois, envoie-moi ta rumeur avant 12:00")	

							else :

								await dm_channel.send(f"Tu ne peux pas m'envoyer une rumeur, tu ne participes pas à la partie")

						else :

							await dm_channel.send(f"Tu te trompe d'événement, l'événement d'aujourd'hui est {self.vars['event']}")

					else :

						await dm_channel.send(f"Aucune partie en cours")

				#==============#
				# KILLER GUESS #
				#==============#

				elif re.match(r"[Kk]iller guess : .*", message.content.lower()) :
					match = re.match(r"[Kk][Ii][Ll][Ll][Ee][Rr] [Gg][Uu][Ee][Ss][Ss] : (.*)", message.content)

					if self.vars['game_started'] :

						if self.vars["event"] == "killer guess" :

							if self.members[author_name]["state"] == "en vie" :

								if (message.created_at.hour+2)%24<12 :

									if match.group(1) in self.members :

										self.events["killer guess"][author_name] = match.group(1)
										await dm_channel.send(f"C'est noté ! Ta réponse a été enregistrée.")
										await self.informer(f"**[KILLER GUESS]** - :grey_question: Le joueur {author_name} pense que {match.group(1)} est son killer\n\u200B")
										self.write_events()

									else :

										await dm_channel.send(f"Je ne connais pas le membre {match.group(1)}, es-tu sûr(e) de l'avoir correctement écris ? N'oublie pas d'écrire son identifiant (par exemple, pour Robin il faut écrire M1k3y#8704 et non M1k3y)")

								else :

									await dm_channel.send("Malheureusement, il est trop tard pour participer à l'événement. La prochaine fois, participe avant 12:00.")

							else :

								await dm_channel.send(f"Seuls les joueurs en vie peuvent participer à cet événement")

						else :

							await dm_channel.send(f"Tu te trompe d'événement, l'événement d'aujourd'hui est {self.vars['event']}")

					else :

						await dm_channel.send(f"Aucune partie en cours")

				#==============================#
				# LISTE DES ANCIENNES MISSIONS #
				#==============================#

				elif re.match(r"liste.*anciennes.*missions", message.content.lower()) :

					await dm_channel.send(f"Voici la liste des missions inventées par les joueurs ayant participé aux précédentes parties de killer :\n")

					for member in self.members :

						for mission in self.missions[member] :

							if mission != "" :

								await dm_channel.send(f"- {mission[::-1]}\n")

				#=============================#
				# DONNER UNE ANCIENNE MISSION #
				#=============================#

				elif re.match(r"[Aa]ncienne mission : (.*)", message.content) :
					match = re.match(r"[Aa]ncienne mission : (.*)", message.content)

					if match.group(1) not in self.missions[author_name] :
						self.missions[author_name].append(match.group(1)[::-1])
						self.write_missions()
						await dm_channel.send(f"J'ai ajouté cette mission à ma liste de missions. Merci :slight_smile:")
					else :
						await dm_channel.send(f"Je connais déjà cette mission, merci quand même :slight_smile:")

				#===================================#
				# DEMANDER LES RÈGLES DU JEU AU BOT #
				#===================================#

				elif re.match(rules_regexp, message.content) :

					await self.send_rules(author_name)
					await self.log_channel.send(f"Règles du jeu envoyées à {author_name}")

				#======#
				# HELP #
				#======#

				elif re.match(r"[Hh]elp.*", message.content) :

					msg_list = []
					msg_list.append(f"Inscription à une partie :\n\\> [Mm]ission : <mission>\n\u200B")
					msg_list.append(f"Désinscription d'une partie :\n\\> [Jj]e ne veux plus jouer\n\u200B")
					msg_list.append(f"Tenter de dénoncer son killer :\n\\> [Mm]on killer est <pseudo>\n\u200B")
					msg_list.append(f"Annoncer au bot qu'on a tué sa cible :\n\\> [Gg]otcha\n\u200B")
					msg_list.append(f"S'inscrire à la gazette :\n\\> [Gg]azette\n\u200B")
					msg_list.append(f"Envoyer une message à son killer :\n\\> [Mm]essage killer : <message>\n\u200B")

					msg_list.append(f"Répandre une rumeur (événement \"rumeurs\") :\n\\> [Rr]umeur : <rumeur>\n\u200B")
					msg_list.append(f"Tenter de trouver son killer (événement \"killer guess\") :\n\\> [Kk]iller guess : <pseudo>\n\u200B")
					msg_list.append(f"Annoncer au bot qu'on a réalisé sa mission (événement paranoïa) :\n\\> [Pp]arano{'{ïa}'} <pseudo>\n\u200B")

					msg_list.append(f"Demander la liste des anciennes missions :\n\\> r\".\\*liste.\\*anciennes.\\*missions.\\*\"\n\u200B")
					msg_list.append(f"Donner une ancienne mission au bot :\n\\> [Aa]ncienne mission : <mission>\n\u200B")

					msg_list.append(f"Demander les règles du jeu :\n\\> [Rr][eè]gles\n\u200B")

					msg_list.append(f"Obtenir la liste des prénoms associés à chaque pseudo du serveur :\n\\> [Pp]seudo\n\u200B")
					msg_list.append(f"Renseigner son prénom :\n\\> [Pp]r[ée]nom : <prénom>\n\u200B")

					for msg in msg_list :
						await dm_channel.send(msg)

				#==========================#
				# CONVERSION PSEUDO/PRÉNOM #
				#==========================#

				elif re.match(r"[Pp]seudo", message.content) :

					msg = f"Voici les prénoms des gens du seveur :\n\n"

					for member in self.members :

						msg += f"- {member} : {self.members[member]['prenom']}\n"

					await dm_channel.send(msg)

				#=======================#
				# RENSEIGNER SON PRÉNOM #
				#=======================#

				elif re.match(r"[Pp]r[ée]nom : (.*)", message.content) :

					prenom = re.match(r"[Pp]r[ée]nom : (.*)", message.content).group(1)
					self.members[author_name]['prenom'] = prenom
					self.write_members()

					liste_prenoms = [
						"Jean-Bernard",
						"Patrick",
						"Monique",
						"Christophe",
						"Baptiste",
						"Kevin",
						"Marie",
						"Bernadette"
					]
					await dm_channel.send(f"C'est noté, désormais tu t'appelles {liste_prenoms[random.randint(0,len(liste_prenoms)-1)]}")

				elif message.author.id != bot_owner_id :

					await dm_channel.send(f"Je n'ai pas compris ton message, es-tu sûr(e) d'avoir utilisé le bon format ? Tu peux m'envoyer \"help\" pour obtenir la liste des formats de message que je connais")