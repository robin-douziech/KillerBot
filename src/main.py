from dotenv import load_dotenv
import os
import logging
import re
import random
from datetime import datetime
import asyncio
from discord.ext import tasks, commands

from KillerBot import *

load_dotenv()

bot = KillerBot(members_file, missions_file, events_file, vars_file, infos_file)

@bot.event
async def on_ready() :

	bot.bot_guild = bot.get_guild(bot_guild_id)
	bot.bot_channel = bot.bot_guild.get_channel(bot_channel_id)
	bot.log_channel = bot.bot_guild.get_channel(log_channel_id)
	bot.gazette_channel = bot.bot_guild.get_channel(gazette_channel_id)

	await bot.log_channel.send(f"KillerBot redémarre ...")

	# liste des membre non-bot du serveur
	tmp_members = []
	for member in bot.bot_guild.members :
		if not(member.bot) :
			tmp_members.append(f"{member.name}#{member.discriminator}")
			if member.dm_channel == None :
				await member.create_dm()

	#################################################
	# METTRE À JOUR LA LISTE DES MEMBRES DU SERVEUR #
	#################################################

	with open(bot.members_file, "rt") as f_members :
		bot.members = json.load(f_members)

	# ajout des nouveaux membres (arrivée pendant que le bot était éteint)
	for member in tmp_members :
		if member not in bot.members :
			bot.members[member] = {
				# member IDs
				"name"   : member.split('#')[0],
				"id"     : member.split('#')[1],
				"last_msg_id" : "0",
				"questioned"  : False,
				"current_question" : "",
				"other_questions"  : [],
				# current game
				"state"            : "non-inscrit",
				"tags"             : [],
				"proposed mission" : "",
				"mission to do"    : "",
				"target"           : "",
				"kills_game"       : "0",
				"msg_sent"         : False,
				# general stats
				"wins"               : '0',
				"kills"              : '0',
				"killers found"      : "0",
				"targets abused"     : "0",
				"get found"          : "0",
				"wrong killer guess" : "0",
				"deaths"             : '0',
				"games_played"       : '0'
			}

	# Suppression des membres partis pendant que le bot était éteint
	members_to_remove = []
	for member in bot.members :
		if member not in tmp_members :
			members_to_remove.append(member)
	for member in members_to_remove :
		bot.members.pop(member)
	bot.write_members()

	dic_member_vars = {
		# member IDs
		"prenom" : "Jean-Bernard",
		"last_msg_id" : "0",
		"questioned"  : False,
		"current_question" : "",
		"other_questions"  : [],
		# current game
		"state"            : "non-inscrit",
		"tags"             : [],
		"proposed mission" : "",
		"mission to do"    : "",
		"target"           : "",
		"kills_game"       : "0",
		"msg_sent"         : False,
		# general stats
		"wins"               : '0',
		"kills"              : '0',
		"killers found"      : "0",
		"targets abused"     : "0",
		"get found"          : "0",
		"wrong killer guess" : "0",
		"deaths"             : '0',
		"games_played"       : '0'
	}

	# on ajoute les variables manquantes
	# (sert à ajouter les nouvelle variables automatiquement quand j'ajoute des variables pour les membres)
	for member in bot.members :
		for var in dic_member_vars :
			if var not in bot.members[member] :
				bot.members[member][str(var)] = dic_member_vars[var]
	bot.write_members()

	#######################################
	# RÉCUPÉRATION DES ANCIENNES MISSIONS #
	#######################################

	with open(bot.missions_file, "rt") as f_missions :
		bot.missions = json.load(f_missions)

	for member in bot.members :
		if member not in bot.missions :
			bot.missions[member] = []
	bot.write_missions()

	##############################
	# RÉCUPÉRATION DES VARIABLES #
	##############################

	with open(bot.vars_file, "rt") as f_vars :
		bot.vars = json.load(f_vars)

	##########################
	# RÉCUPÉRATION DES INFOS #
	##########################

	with open(bot.infos_file, "rt") as f_infos :
		bot.infos = json.load(f_infos)

	###############################
	# RÉCUPÉRATION DES ÉVÉNEMENTS #
	###############################

	with open(bot.events_file, "rt") as f_events :
		bot.events = json.load(f_events)

	# rumeurs
	for member in bot.members :
		if member not in bot.events["rumeurs"] :
			bot.events["rumeurs"][member] = ""

	#killer guess
	for member in bot.members :
		if member not in bot.events["killer guess"] :
			bot.events["killer guess"][member] = ""

	# ville fantôme
	for member in bot.members :
		if member not in bot.events["ville fantôme"] :
			bot.events["ville fantôme"][member] = {
				"previous target": "",
				"target" : "",
				"mission" : ""
			}

	bot.write_events()

	###################
	# PARTIE EN COURS #
	###################

	msg = ""
	if bot.vars['game_started'] :
		msg = f"Une partie est en cours.\nParticipants (vivants et morts) :\n"
		for member in bot.members :
			if bot.members[member]["state"] in ["mort", "en vie"] :
				msg += f"- {member}\n"
	else :
		msg = f"Aucune partie en cours.\nInscrits à la prochaine partie :\n"
		for member in bot.members :
			if bot.members[member]["state"] == "inscrit" :
				msg += f"- {member}\n"
	await bot.log_channel.send(msg)

	#####################################################################
	# TRAITER LES MESSAGES REÇUS HORS LIGNE (DANS L'ORDRE DE RÉCEPTION) #
	#####################################################################

	RECEIVED_MESSAGES = []

	for member in bot.members :

		if int(bot.members[member]["last_msg_id"]) > 0 :

			Member = bot.fetch_member(member)
			messages = []
			last_msg_members_file = await Member.dm_channel.fetch_message(bot.members[member]["last_msg_id"])
			last_msg_real = None
			index = 0

			while last_msg_real != last_msg_members_file :

				index += 1

				messages = [message async for message in bot.fetch_member(member).dm_channel.history(limit=index)]
				last_msg_real = messages[-1]

			for message in messages[:-1] :

				if message.author != bot.user :
					RECEIVED_MESSAGES.append(message)

	SORTED_RECEIVED_MESSAGES = bot.sort_messages(RECEIVED_MESSAGES)
	for message in SORTED_RECEIVED_MESSAGES :
		await bot.process_msg(message)

	bot.log(f"{bot.user.display_name} est prêt.")
	await bot.log_channel.send(f"{bot.user.display_name} est prêt.")

	clock.start()

@bot.event
async def on_member_join(member) :

	if member in bot.bot_guild.members and not(member in bot.members) :

		bot.members[member] = {
			# member IDs
			"name"   : member.split('#')[0],
			"id"     : member.split('#')[1],
			"last_msg_id" : "0",
			"questioned"  : False,
			"current_question" : "",
			"other_questions"  : [],
			# current game
			"state"            : "non-inscrit",
			"tags"             : [],
			"proposed mission" : "",
			"mission to do"    : "",
			"target"           : "",
			"kills_game"       : "0",
			"msg_sent"         : False,
			# general stats
			"wins"           : '0',
			"kills"          : '0',
			"killers found"  : "0",
			"targets abused" : "0",
			"deaths"         : '0',
			"games_played"   : '0'
		}
		bot.write_members()

@bot.event
async def on_member_remove(member) :

	if member in bot.members and not(member in bot.bot_guild.members) :

		bot.members.pop(member)
		bot.write_members()

@bot.event
async def on_message(message) :

	await bot.process_msg(message)

@tasks.loop(seconds = 60)
async def clock() :

	now = datetime.now().strftime('%H:%M')
	h = now.split(':')[0]
	m = now.split(':')[1]
	now = f"{(int(h)+bot.vars['clock_hours_offset'])%24}:{m}"

	if bot.vars['game_started'] :

		#==================#
		# NOUVELLE JOURNÉE #
		#==================#

		if now == "0:00":

			bot.vars["day"] += 1

			nb_deaths = 0
			for member in bot.members :
				bot.members[member]['msg_sent'] = False

				if bot.members[member]['state'] == "mort" :
					nb_deaths += 1

			if nb_deaths >= 3 :
				bot.events['ville fantôme']['active'] = True
				bot.events['paranoïa']['active'] = True
			else :
				bot.events['ville fantôme']['active'] = False
				bot.events['paranoïa']['active'] = False

			# choisir un event
			bot.vars["event"] = bot.choose_event()
			await bot.process_event()

			# désactiver ville fantôme si on tombe dessus
			if bot.vars["event"] == "ville fantôme" :
				bot.events["ville fantôme"]["active"] = False

			# la gazette des gens morts
			numbers = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]

			number = f':{numbers[bot.vars["day"]]}:' if bot.vars['day']<=10 else f'{bot.vars["day"]}'
			await bot.informer(f"#================ JOUR {number} ================#\n\n__Événement du jour__ : {bot.vars['event']}\n\u200B")

			bot.write_members()
			bot.write_events()
			bot.write_vars()

		#=========#
		# RUMEURS #
		#=========#

		if now == "12:30" and bot.vars["event"] == "rumeurs" :

			# on annonce les rumeurs dans un ordre aléatoire
			msg = f"**[RUMEURS]** - Voici toutes les rumeurs qui m'ont été transmises par les joueurs :\n\n"
			liste_rumeurs = []
			for member in bot.members :
				if bot.events["rumeurs"][member] != "" :
					liste_rumeurs.append(bot.events['rumeurs'][member])
			random.shuffle(liste_rumeurs)
			for rumeur in liste_rumeurs :
				msg += f"- {rumeur}\n"
			msg += f"\u200B"		
			await bot.bot_channel.send(msg)

		#==============#
		# KILLER GUESS #
		#==============#

		if now == "12:30" and bot.vars["event"] == "killer guess" :

			nb_found = 0
			for member in bot.members :

				killer = bot.find_killer(member)
				Killer = bot.fetch_member(killer)

				if bot.events["killer guess"][member] != "" :
					if bot.events["killer guess"][member] == killer :
						await Killer.dm_channel.send(f"**[KILLER GUESS]** - Ta cible a deviné ton identité lors du killer guess :grimacing:")
						nb_found += 1

			if nb_found == 0 :
				await bot.bot_channel.send(f"**[KILLER GUESS]** - Personne ne m'a donné la véritable identité de son killer")
			else :
				await bot.bot_channel.send(f"**[KILLER GUESS]** - {nb_found} joueur{'s' if nb_found>1 else ''} m'{'ont' if nb_found>1 else 'a'} donné la véritable identité de {'leur' if nb_found>1 else 'son'} killer.")

		#============#
		# FLASH INFO #
		#============#

		if now in ['8:00', '10:00', '12:00', '15:00', '18:00', '22:00'] :

			await bot.flash_info()

bot.run(os.getenv("TOKEN"))