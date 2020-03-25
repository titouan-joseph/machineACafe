# bot.py
import os
import re
import random

import discord
from dotenv import load_dotenv
from time import sleep
import sqlite3

# connecting to the sqlite3 database to store players score
conn = sqlite3.connect("users.db")
c = conn.cursor()

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()
state = 0
messages = {}
courreurs = []
parieurs = []

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    
    ########################## PARTIE CAFE ###################################

    if (re.match("(.)*(cafe|café|kfé|kfe|kaf|caf)(.)*", message.content) and not message.author.bot):
        # génération aléatoire du message
        rand = random.randint(1, 10)
        if rand == 1:
            await message.channel.send("Plus de gobelets déso pas déso")
        elif rand == 2:
            await message.channel.send("Tiens, Je rend pas la monaie par contre...")
        else:
            await message.channel.send("Bzz voila ton café :)")
    
    ########################## PARTIE COURSES ###################################
    
    global state, messages, courreurs, parieurs
    
    if (message.content == "$course" and not message.author.bot and state == 0):
        state+= 1
        messages["concurrents"] = await message.channel.send("Choisissez les émojis qui vont faire la course, ensuite envoyez $ready")
        messages["course"] = message

    elif (message.content == "$ready" and not message.author.bot and state == 1):
        if (messages["concurrents"].reactions):
            state += 1
            messages["paris"] = await message.channel.send("Faites vos paris ! ensuite envoyez $start")
            
            for reaction in messages["concurrents"].reactions:
                
                #montre les possibilités de vote
                await messages["paris"].add_reaction(reaction)
                
                # création de la course
                courreurs.append({ 'reaction': reaction, 'avance': 1, 'votes': [], 'course': None})

            messages["ready"] = message
        else:
            await message.channel.send("Il faut au moins un competiteur")

    elif (message.content == "$start" and not message.author.bot and state == 2):
        state += 1
        # message recap des paris
        for courreur in courreurs:
            usersList = ""
            if not courreur["votes"]:
                usersList = "Personne n'"
            for user in courreur["votes"]:
                usersList += user.name + ", "
            await message.channel.send("{} a.ont parié.e.s pour {}".format(usersList, courreur["reaction"].emoji))
        # affichage de la course
        await message.channel.send("---------------------- Debut de la course ----------------------")
        for courreur in courreurs:            
            courreur["course"] = await message.channel.send(':checkered_flag:' + courreur["avance"] * " " + courreur["reaction"].emoji + (200 - courreur["avance"]) * " " + ":triangular_flag_on_post:")
            
        # on fait la course !!!
        while True:
            # on avance un courreur random
            courreur = courreurs[random.randint(0, len(courreurs) - 1)]
            currentCourse = courreur["course"]
            courreur["avance"] += random.randint(1, 10)
            if (courreur["avance"] >= 20):
                await message.channel.send("---------------------- Fin de la course ----------------------")
                strCourseFin = ":checkered_flag:" + 200 * " " + ":triangular_flag_on_post:" + courreur["reaction"].emoji
                await currentCourse.edit(content=strCourseFin)
                break
            strCourse = ":checkered_flag:" + courreur["avance"] * " " + courreur["reaction"].emoji + (200 - courreur["avance"]) * " " + ":triangular_flag_on_post:"
            await currentCourse.edit(content=strCourse)
            sleep(random.random() * 0.3 + 0.1)

        podium = sorted(courreurs, key=lambda i: i["avance"], reverse=True)

        # update en meme temps dans la base de donnée 
        try:
            await message.channel.send(":first_place: " + podium[0]["reaction"].emoji)
            for parieur in podium[0]["votes"]:
                c.execute(f'INSERT OR IGNORE INTO users VALUES ({parieur.id}, "{parieur.name}", 0, 0);')
                c.execute(f'UPDATE users SET balance = balance +  5, nbBets = nbBets + 1 WHERE id LIKE {parieur.id};')
                await message.channel.send(f'{parieur.name} a gagné 5 tc-dollars')

            await message.channel.send(":second_place: " + podium[1]["reaction"].emoji)
            for parieur in podium[1]["votes"]:
                c.execute(f'INSERT OR IGNORE INTO users VALUES ({parieur.id}, "{parieur.name}", 0, 0);')
                c.execute(f'UPDATE users SET balance = balance +  3, nbBets = nbBets + 1 WHERE id LIKE {parieur.id};')
                await message.channel.send(f'{parieur.name} a gagné 3 tc-dollars')

            await message.channel.send(":third_place: " + podium[2]["reaction"].emoji)
            for parieur in podium[2]["votes"]:
                c.execute(f'INSERT OR IGNORE INTO users VALUES ({parieur.id}, "{parieur.name}", 0, 0);')
                c.execute(f'UPDATE users SET balance = balance +  1, nbBets = nbBets + 1 WHERE id LIKE {parieur.id};')
                await message.channel.send(f'{parieur.name} a gagné 1 tc-dollar')
        
        finally:
            conn.commit() # udpate the changes in db
            state = 0 # back to normal state
            # clear  variables
            messages = {}
            courreurs = []


    elif(message.content == "$scoreboard" and state == 0 and not message.author.bot):
        await message.channel.send(":first_place: ---- Scoreboard ---- :first_place:")
        for index, row in enumerate(c.execute('SELECT u.* FROM users u ORDER BY u.balance DESC LIMIT 10')):
            await message.channel.send(f'{index + 1} --- {row[1]} avec {row[2]} tc-dollars')

    elif(message.content == "$myscore" and state == 0 and not message.author.bot):
        c.execute(f'SELECT * FROM users WHERE id={message.author.id}')
        dbOut = c.fetchone()
        await message.channel.send(f'Tu as gagné {dbOut[2]} tc-dollars en {dbOut[3]} paris')

    elif(message.content == "$help" and state == 0 and not message.author.bot):
        await message.channel.send("Liste des commandes : $course, $scoreboard, $myscore")

@client.event
async def on_reaction_add(reaction, user):
    
    # * Working
    # stockage des reactions aux messages du bot
    if (reaction.message.id == messages["concurrents"].id and reaction not in messages["concurrents"].reactions):
        messages["concurrents"].reactions.append(reaction)
    
    # stockage des paris
    if (state == 2 and reaction.message.id == messages["paris"].id and not user == client.user and user not in parieurs):
        for courreur in courreurs: # on evite les emojis qui ne sont pas en compet
            if (courreur["reaction"].emoji == reaction.emoji):
                courreur["votes"].append(user)
                parieurs.append(user) # evite les doubles votes

client.run(TOKEN)