import discord
import asyncio
from redbot.core import commands, Config
from .ui_elements import SelectFightingStyleView
from .fighting_game import FightingGame
from datetime import datetime, timedelta
import logging

class MemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_records = []

    def emit(self, record):
        self.log_records.append(self.format(record))

    def get_logs(self):
        return self.log_records

    def clear_logs(self):
        self.log_records = []

class Bullshido(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=123123451514345671215451351235890, force_registration=True)
        default_user = {
            "fighting_style": None,
            "wins": {"UD": 0, "SD": 0, "TKO": 0, "KO": 0},
            "losses": {"UD": 0, "SD": 0, "TKO": 0, "KO": 0},
            "level": 1,
            "training_level": 1,
            "nutrition_level": 1,
            "morale": 100,
            "intimidation_level": 0,
            "stamina_level": 100,
            "last_interaction": None,
            "last_command_used": None,
            "last_train": None,
            "last_diet": None,
            "fight_history": []
        }
        
        self.config.register_user(**default_user)
        
        self.logger = logging.getLogger("red.bullshido")
        self.logger.setLevel(logging.DEBUG)
        
        self.memory_handler = MemoryLogHandler()
        self.logger.addHandler(self.memory_handler)
        
        self.file_handler = logging.FileHandler('bullshido.log')
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
        self.file_handler.setFormatter(formatter)
        self.logger.addHandler(self.file_handler)
        
        self.bg_task = self.bot.loop.create_task(self.check_inactivity())
        self.logger.info("Bullshido cog loaded.")
        
    async def has_sufficient_stamina(self, user):
        """ Check if the user has sufficient stamina to fight."""
        stamina = await self.config.user(user).stamina_level()
        return stamina >= 20
    
    async def set_fighting_style(self, interaction: discord.Interaction, new_style: str):
        user = interaction.user
        user_data = await self.config.user(user).all()

        if user_data["fighting_style"] != new_style:
            user_data["fighting_style"] = new_style
            user_data["training_level"] = 0
            await self.config.user(user).set(user_data)
            await self.config.user(user).fighting_style.set(new_style)
            await self.config.user(user).training_level.set(0)
            result = f"Fighting style changed to {new_style} and training level reset to 0."
        else:
            result = "You already have this fighting style."

        await interaction.response.send_message(result)

    async def check_inactivity(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await self.apply_inactivity_penalties()
            await asyncio.sleep(3600)  # Check every hour

    async def apply_inactivity_penalties(self):
        current_time = datetime.utcnow()
        async with self.config.all_users() as users:
            for user_id, user_data in users.items():
                await self.apply_penalty(user_id, user_data, current_time, "train", "training_level")
                await self.apply_penalty(user_id, user_data, current_time, "diet", "nutrition_level")

    async def apply_penalty(self, user_id, user_data, current_time, last_action_key, level_key):
        last_action = user_data.get(f"last_{last_action_key}")
        if last_action:
            last_action_time = datetime.strptime(last_action, '%Y-%m-%d %H:%M:%S')
            if current_time - last_action_time > timedelta(days=2):
                # Apply penalty if the user missed a day
                new_level = max(1, user_data[level_key] - 20)
                await self.config.user_from_id(user_id)[level_key].set(new_level)
                user = self.bot.get_user(user_id)
                if user:
                    await user.send(f"You've lost 20 points in your {level_key.replace('_', ' ')} due to inactivity.")
                await self.config.user_from_id(user_id)[f"last_{last_action_key}"].set(current_time.strftime('%Y-%m-%d %H:%M:%S'))

    async def update_intimidation_level(self, user: discord.Member):
        user_data = await self.config.user(user).all()
        ko_wins = user_data["wins"]["KO"]
        tko_wins = user_data["wins"]["TKO"]
        intimidation_level = ko_wins + tko_wins
        await self.config.user(user).intimidation_level.set(intimidation_level)

    @commands.hybrid_group(name="bullshido", description="Commands related to the Bullshido game")
    async def bullshido_group(self, ctx: commands.Context):
        pass

    @bullshido_group.command(name="log", description="Displays the log")
    async def show_log(self, ctx: commands.Context):
        """Displays the Bullshido log."""
        logs = self.memory_handler.get_logs()
        if not logs:
            await ctx.send("No logs available.")
            return
        for chunk in [logs[i:i+10] for i in range(0, len(logs), 10)]:
            await ctx.send("```\n{}\n```".format("\n".join(chunk)))

    @bullshido_group.command(name="setstyle", description="Select your fighting style")
    async def select_fighting_style(self, ctx: commands.Context):
        """Prompts the user to select their fighting style."""
        view = SelectFightingStyleView(self.set_fighting_style, ctx.author, ctx)
        await ctx.send("Please select your fighting style:", view=view)

    @bullshido_group.command(name="train", description="Train daily to increase your Bullshido training level")
    async def train(self, ctx: commands.Context):
        """Train daily to increase your Bullshido training level."""
        user = ctx.author
        style = await self.config.user(user).fighting_style()
        
        # Check if the command was used in the last 24 hours
        last_train = await self.config.user(user).last_train()
        if last_train:
            last_train_time = datetime.strptime(last_train, '%Y-%m-%d %H:%M:%S')
            if datetime.utcnow() - last_train_time < timedelta(hours=24):
                await ctx.send(f"{user.mention}, you can only use the train command once every 24 hours.")
                return

        # Update the last train time before executing the command to avoid timing issues
        await self.config.user(user).last_train.set(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Increment training level
        new_training_level = await self.increment_training_level(user)
        await ctx.send(f"{user.mention} has successfully trained in {style}! Your training level is now {new_training_level}.")

    @bullshido_group.command(name="diet", description="Focus on your diet to increase your nutrition level")
    async def diet(self, ctx: commands.Context):
        """Focus on your diet to increase your nutrition level."""
        user = ctx.author
        
        # Check if the command was used in the last 24 hours
        last_diet = await self.config.user(user).last_diet()
        if last_diet:
            last_diet_time = datetime.strptime(last_diet, '%Y-%m-%d %H:%M:%S')
            if datetime.utcnow() - last_diet_time < timedelta(hours=24):
                await ctx.send(f"{user.mention}, you can only use the diet command once every 24 hours.")
                return

        # Update the last diet time before executing the command to avoid timing issues
        await self.config.user(user).last_diet.set(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Increment nutrition level
        new_nutrition_level = await self.increment_nutrition_level(user)
        await ctx.send(f"{user.mention} has followed their specialized diet today and gained nutrition level! Your nutrition level is now {new_nutrition_level}.")

    async def increment_training_level(self, user):
        user_data = await self.config.user(user).all()
        new_training_level = user_data['training_level'] + 10
        await self.config.user(user).training_level.set(new_training_level)
        return new_training_level
    
    async def increment_stamina_level(self, user):
        stamina_level = await self.config.user(user).stamina_level()
        new_stamina_level = stamina_level + 10
        await self.config.user(user).training_level.set(new_stamina_level)
        return new_stamina_level

    async def increment_nutrition_level(self, user):
        user_data = await self.config.user(user).all()
        new_nutrition_level = user_data['nutrition_level'] + 10
        await self.config.user(user).nutrition_level.set(new_nutrition_level)
        return new_nutrition_level

    async def update_daily_interaction(self, user, command_used):
        user_data = await self.config.user(user).all()
        today = datetime.utcnow().date()
        
        last_interaction = user_data.get(f'last_{command_used}')
        if last_interaction:
            last_interaction_date = datetime.strptime(last_interaction, '%Y-%m-%d %H:%M:%S').date()
            if today - last_interaction_date > timedelta(days=1):
                # Apply penalty if the user missed a day
                if command_used == "train":
                    new_training_level = max(1, user_data['training_level'] - 20)
                    await self.config.user(user).training_level.set(new_training_level)
                elif command_used == "diet":
                    new_nutrition_level = max(1, user_data['nutrition_level'] - 20)
                    await self.config.user(user).nutrition_level.set(new_nutrition_level)
                await user.send(f"You've lost 20 points in your {command_used} level due to inactivity.")
        
        # Update the user's config for today
        await self.config.user(user)[f'last_{command_used}'].set(today.strftime('%Y-%m-%d %H:%M:%S'))

    @bullshido_group.command(name="list_fighting_styles", description="List all available fighting styles")
    async def list_fighting_styles(self, ctx: commands.Context):
        """List all available fighting styles."""
        styles = ["Karate", "Muay-Thai", "Aikido", "Boxing", "Kung-Fu", "Judo", "Taekwondo", "Wrestling", "Sambo", "MMA", "Capoeira", "Kickboxing", "Krav-Maga", "Brazilian Jiu-Jitsu"]
        await ctx.send(f"Available fighting styles: {', '.join(styles)}")
    
    @bullshido_group.command(name="fight", description="Start a fight with another player")
    async def fight(self, ctx: commands.Context, opponent: discord.Member):
        """Start a fight with another player."""
        await ctx.defer()
        try: 
            player1 = ctx.author
            player2 = opponent
            
            player1_data = await self.config.user(player1).all()
            player2_data = await self.config.user(player2).all()
            
            if not await self.has_sufficient_stamina(player1):
                await ctx.send(f"You are too tired to fight,  {player1.mention}.\n Try waiting some time for your stamina to recover, or buy some supplements to speed up your recovery.")
                return
            if not await self.has_sufficient_stamina(player2):
                await ctx.send("Your opponent does not have enough stamina to start the fight.")
                return
            
            if not player1_data['fighting_style'] or not player2_data['fighting_style']:
                await ctx.send("Both players must have selected a fighting style before starting a fight.")
                return
            if player1 == player2:
                await ctx.send("You cannot fight yourself, only your own demons! Try challenging another fighter.")
                return
            
            # Set up an instance of game session
            game = FightingGame(self.bot, ctx.channel, player1, player2, player1_data, player2_data, self)
            await game.start_game()
            
        except Exception as e:
            self.logger.error(f"Failed to start fight: {e}")
            await ctx.send(f"Failed to start the fight due to an error: {e}")

    @bullshido_group.command(name="reset_stats", description="Resets all Bullshido user data to default values")
    async def reset_stats(self, ctx: commands.Context):
        """Reset the Bullshido Redbot Configuration values to default for all users."""
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.upper() == "YES"

        # Send confirmation message
        await ctx.send("Are you sure you want to reset Bullshido user data? Type 'YES' to confirm.")

        try:
            # Wait for a response for 30 seconds
            confirmation = await self.bot.wait_for('message', check=check, timeout=30.0)
            if confirmation:
                # If confirmed, reset all config values
                default_user = {
                    "fighting_style": None,
                    "wins": {"UD": 0, "SD": 0, "TKO": 0, "KO": 0},
                    "losses": {"UD": 0, "SD": 0, "TKO": 0, "KO": 0},
                    "level": 1,
                    "training_level": 1,
                    "nutrition_level": 1,
                    "morale": 100,
                    "intimidation_level": 0,
                    "stamina_level": 100,
                    "last_interaction": None,
                    "last_command_used": None,
                    "last_train": None,
                    "last_diet": None,
                    "fight_history": []
                }

                async with self.config.all_users() as all_users:
                    for user_id in all_users:
                        user_config = self.config.user_from_id(user_id)
                        for key, value in default_user.items():
                            await user_config.set_raw(key, value=value)

                await ctx.send("All config values have been reset to default.")
        except asyncio.TimeoutError:
            await ctx.send("Reset operation cancelled due to timeout.")

    @bullshido_group.command(name="reset_config", description="Resets Bullshido configuration to default values")
    async def reset_config(self, ctx: commands.Context):
        """Resets Bullshido configuration to default values."""
        await self.config.clear_all_users()
        await ctx.send("Bullshido configuration has been reset to default values.")

    @bullshido_group.command(name="player_stats", description="Displays your wins and losses", aliases=["stats"])
    async def player_stats(self, ctx: commands.Context):
        """Displays your wins and losses."""
        user = ctx.author
        wins = await self.config.user(user).wins()
        losses = await self.config.user(user).losses()
        level = await self.config.user(user).level()
        training_level = await self.config.user(user).training_level()
        nutrition_level = await self.config.user(user).nutrition_level()
        morale = await self.config.user(user).morale()
        intimidation_level = await self.config.user(user).intimidation_level()
        fighting_style = await self.config.user(user).fighting_style()
        stamina = await self.config.user(user).stamina_level()

        total_wins = sum(wins.values())
        total_losses = sum(losses.values())

        embed = discord.Embed(title=f"{user.display_name}'s Fight Record", color=0xFF0000)
        embed.add_field(name="Total Wins", value=total_wins, inline=True)
        embed.add_field(name="Total Losses", value=total_losses, inline=True)
        embed.add_field(name="Wins (UD)", value=wins["UD"], inline=True)
        embed.add_field(name="Wins (SD)", value=wins["SD"], inline=True)
        embed.add_field(name="Wins (TKO)", value=wins["TKO"], inline=True)
        embed.add_field(name="Wins (KO)", value=wins["KO"], inline=True)
        embed.add_field(name="Losses (UD)", value=losses["UD"], inline=True)
        embed.add_field(name="Losses (SD)", value=losses["SD"], inline=True)
        embed.add_field(name="Losses (TKO)", value=losses["TKO"], inline=True)
        embed.add_field(name="Losses (KO)", value=losses["KO"], inline=True)
        embed.add_field(name=f"{user.display_name}'s Current Stats", value="\u200b", inline=False)
        embed.add_field(name="Fighting Style", value=fighting_style, inline=True)
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="Training Level", value=training_level, inline=True)
        embed.add_field(name="Nutrition Level", value=nutrition_level, inline=True)
        embed.add_field(name="Morale", value=morale, inline=True)
        embed.add_field(name="Intimidation Level", value=intimidation_level, inline=True)
        embed.add_field(name="Stamina", value=stamina, inline=True)
        embed.set_thumbnail(url="https://i.ibb.co/7KK90YH/bullshido.png")
        await ctx.send(embed=embed)

    @bullshido_group.command(name="fight_record", description="Displays the results of your last 10 fights")
    async def fight_record(self, ctx: commands.Context):
        """Displays the results of your last 10 fights."""
        user = ctx.author
        fight_history = await self.config.user(user).fight_history()

        if not fight_history:
            await ctx.send("You have no fight history.")
            return

        embed = discord.Embed(title=f"{user.display_name}'s Last 10 Fights", color=0xFF0000)

        for fight in fight_history[-10:]:
            outcome = fight.get("outcome", "Unknown")
            opponent = fight.get("opponent", "Unknown")
            result_type = fight.get("result_type", "Unknown")
            embed.add_field(name=f"Fight vs {opponent}", value=f"Outcome: {outcome}, Result: {result_type}", inline=False)

        embed.set_thumbnail(url="https://i.ibb.co/7KK90YH/bullshido.png")
        await ctx.send(embed=embed)

    async def get_player_data(self, user):
        fighting_style = await self.config.user(user).fighting_style()
        level = await self.config.user(user).level()
        training_level = await self.config.user(user).training_level()
        nutrition_level = await self.config.user(user).nutrition_level()
        morale = await self.config.user(user).morale()
        intimidation_level = await self.config.user(user).intimidation_level()
        wins = await self.config.user(user).wins()
        losses = await self.config.user(user).losses()
        fight_history = await self.config.user(user).fight_history()
        return {
            "fighting_style": fighting_style,
            "wins": wins,
            "losses": losses,
            "level": level,
            "training_level": training_level,
            "nutrition_level": nutrition_level,
            "morale": morale,
            "intimidation_level": intimidation_level,
            "fight_history": fight_history
        }
    
    async def update_player_stats(self, user, win, result_type, opponent_name):
        try:
            current_wins = await self.config.user(user).wins()
            current_losses = await self.config.user(user).losses()
            fight_history = await self.config.user(user).fight_history()

            outcome = "Win" if win else "Loss"

            fight_history.append({
                "opponent": opponent_name,
                "outcome": outcome,
                "result_type": result_type
            })

            if win:
                new_wins = current_wins.copy()
                new_wins[result_type] += 1
                await self.config.user(user).wins.set(new_wins)
                self.logger.debug(f"Updated wins for {user.display_name}: {current_wins} -> {new_wins}")
            else:
                new_losses = current_losses.copy()
                new_losses[result_type] += 1
                await self.config.user(user).losses.set(new_losses)
                self.logger.debug(f"Updated losses for {user.display_name}: {current_losses} -> {new_losses}")

            # Update the fight history
            await self.config.user(user).fight_history.set(fight_history)
            await self.update_intimidation_level(user)

        except Exception as e:
            self.logger.error(f"Error updating stats for {user.display_name}: {e}")


    def create_health_bar(self, current_health, max_health):
        progress = current_health / max_health
        progress_bar_length = 50  
        progress_bar_filled = int(progress * progress_bar_length)
        progress_bar = "[" + ("=" * progress_bar_filled)
        progress_bar += "=" * (progress_bar_length - progress_bar_filled) + "]"
        if progress_bar_filled < progress_bar_length:  
            marker = "🔴"
            progress_bar = progress_bar[:progress_bar_filled] + marker + progress_bar[progress_bar_filled + 1:]
        return progress_bar


    @bullshido_group.command(name="clear_old_config", description="Clears old configuration to avoid conflicts")
    async def clear_old_config(self, ctx: commands.Context):
        """Clears old configuration to avoid conflicts."""
        await self.config.clear_all_users()
        await ctx.send("Old Bullshido configuration has been cleared.")

async def setup(bot):
    await bot.add_cog(Bullshido(bot))
