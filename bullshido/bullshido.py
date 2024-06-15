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
            "wins": 0,
            "losses": 0,
            "level": 1,
            "training_level": 1,
            "nutrition_level": 1,
            "morale": 100,
            "intimidation_level": 0,
            "stamina_level": 100,
            "last_interaction": None,
            "last_command_used": None,
            "last_train": None,
            "last_diet": None
        }
        self.config.register_user(**default_user)
        self.logger = logging.getLogger("red.bullshido")
        self.memory_handler = MemoryLogHandler()
        self.logger.addHandler(self.memory_handler)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
        self.memory_handler.setFormatter(formatter)
        self.logger.setLevel(logging.DEBUG)

    async def set_fighting_style(self, ctx: commands.Context, user: discord.Member, style: str):
        await self.config.user(user).fighting_style.set(style)
        await ctx.send(f"{user.mention} has trained in the style of {style}!")

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
    
    @bullshido_group.command(name="commands", description="Displays the Bullshido game commands")
    async def bullshido_commands(self, ctx: commands.Context):
        """Displays information about the Bullshido game commands."""
        embed = discord.Embed(title="Bullshido Game Commands", description="Learn how to play and interact with the Bullshido game.", color=0x00ff00)
        embed.add_field(name="/bullshido select_fighting_style", value="Select your fighting style.", inline=False)
        embed.add_field(name="/bullshido list_fighting_styles", value="List all available fighting styles.", inline=False)
        embed.add_field(name="/bullshido fight", value="Start a fight with another player.", inline=False)
        embed.add_field(name="/bullshido commands", value="Displays information about the Bullshido game commands.", inline=False)
        embed.add_field(name="/bullshido player_stats", value="Displays your wins and losses.", inline=False)
        embed.add_field(name="/bullshido train", value="Train daily to increase your Bullshido training level.", inline=False)
        embed.add_field(name="/bullshido diet", value="Focus on your diet to increase your nutrition level.", inline=False)
        embed.add_field(name="/bullshido about", value="Displays information about the Bullshido game.", inline=False)
        embed.set_image(url="https://i.ibb.co/GWpXztm/bullshido.png")
        await ctx.send(embed=embed)
        
    @bullshido_group.command(name="about", description="Learn how the Bullshido game works")
    async def bullshido_about(self, ctx: commands.Context):
        """Provides information about how the Bullshido game works."""
        embed = discord.Embed(
            title="About Bullshido",
            description="Welcome to Bullshido, a Discord game of epic combat!",
            color=0x00ff00
        )
        embed.add_field(
            name="Selecting a Fighting Style",
            value="Use `/bullshido select_fighting_style` to choose your fighting style. Each style has unique strikes and abilities.",
            inline=False
        )
        embed.add_field(
            name="Daily Training and Diet",
            value="Train and follow a diet each day to improve your stats:\n- `/bullshido train`: Train daily to increase your training level.\n- `/bullshido diet`: Follow a diet to increase your nutrition level.\n*Note: Each can be used once every 24 hours.*\n Your overall nutrition and training level will improve your chances of winning a fight.",
            inline=False
        )
        embed.add_field(
            name="Starting a Fight",
            value="Challenge another player to a fight using `/bullshido fight @player`. The fight consists of 3 rounds and will be scored by a panel of judges, unless a KO/TKO/Submission occurs.",
            inline=False
        )
        embed.add_field(
            name="Winning and Losing",
            value="Winning a fight increases your wins and morale. Losing decreases your morale. Keep training and dieting to improve your chances in future fights.",
            inline=False
        )
        embed.add_field(
            name="Penalties for Inactivity",
            value="If you miss a day of training or diet, your stats will decrease by 20 points.",
            inline=False
        )
        embed.add_field(
            name="Fighting Styles",
            value="Each style has unique strikes and abilities. Use `/bullshido list_fighting_styles` to see all available styles.",
        )
        embed.add_field(
            name="Stamina",
            value="Fighting costs stamina, which will be regained daily, or can be replenished by purchasing stamina recovery items. Use `/bullshido stamina` to see your current stamina level.",
        )
        embed.add_field(
            name="Buy",
            value="Buy stamina recovery items using `/bullshido buy <item>`.",
        )
        embed.set_thumbnail(url="https://i.ibb.co/GWpXztm/bullshido.png")
        await ctx.send(embed=embed)

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

        await self.update_daily_interaction(user, "train")
        await self.config.user(user).last_train.set(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
        await ctx.send(f"{user.mention} has successfully trained in {style}!")

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

        await self.update_daily_interaction(user, "diet")
        await self.config.user(user).last_diet.set(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
        await ctx.send(f"{user.mention} has followed their specialized diet today and gained nutrition level!")
    
    @bullshido_group.command(name="select_fighting_style", description="Select your fighting style")
    async def select_fighting_style(self, ctx: commands.Context):
        """Select your fighting style."""
        view = SelectFightingStyleView(self.set_fighting_style, ctx.author, ctx)
        await ctx.send("Please select your fighting style:", view=view)

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
            
            if not player1_data['fighting_style'] or not player2_data['fighting_style']:
                await ctx.send("Both players must have selected a fighting style before starting a fight.")
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
        # Send confirmation message
        await ctx.send("Are you sure you want to reset Bullshido user data? Type 'YES' to confirm.")

        # Check for the user's response
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.upper() == "YES"

        try:
            # Wait for a response for 30 seconds
            confirmation = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("Reset operation cancelled due to timeout.")
        else:
            # If confirmed, reset all config values
            default_user = {
                "fighting_style": None,
                "wins": 0,
                "losses": 0,
                "level": 1,
                "training_level": 1,
                "nutrition_level": 1,
                "morale": 100,
                "intimidation_level": 0,
                "stamina_level": 100,
                "last_interaction": None,
                "last_command_used": None,
                "last_train": None,
                "last_diet": None
            }
            # Reset config for all users
            async with self.config.all_users() as all_users:
                for user_id in all_users:
                    all_users[user_id].update(default_user)
            await ctx.send("All config values have been reset to 0.")

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

        embed = discord.Embed(title=f"{user.display_name}'s Fight Record", color=0x00ff00)
        embed.add_field(name="Wins", value=wins, inline=True)
        embed.add_field(name="Losses", value=losses, inline=True)
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

    #Get player data from the redbot config 
    async def get_player_data(self, user):
        fighting_style = await self.config.user(user).fighting_style()
        level = await self.config.user(user).level()
        training_level = await self.config.user(user).training_level()
        nutrition_level = await self.config.user(user).nutrition_level()
        morale = await self.config.user(user).morale()
        intimidation_level = await self.config.user(user).intimidation_level()
        wins = await self.config.user(user).wins()
        losses = await self.config.user(user).losses()
        return {"fighting_style": fighting_style, "wins": wins, "losses": losses, "level": level, "training_level": training_level, "nutrition_level": nutrition_level, "morale": morale, "intimidation_level": intimidation_level}
    
    #Update player win and loss stats post round 
    async def update_player_stats(self, user, win=True):
        try:
            current_wins = await self.config.user(user).wins()
            current_losses = await self.config.user(user).losses()
            if win:
                new_wins = current_wins + 1
                await self.config.user(user).wins.set(new_wins)
                self.logger.debug(f"Updated wins for {user.display_name}: {current_wins} -> {new_wins}")
            else:
                new_losses = current_losses + 1
                await self.config.user(user).losses.set(new_losses)
                self.logger.debug(f"Updated losses for {user.display_name}: {current_losses} -> {new_losses}")
        except Exception as e:
            self.logger.error(f"Error updating stats for {user.display_name}: {e}")
            
    async def update_daily_interaction(self, user, command_used):
        user_data = await self.config.user(user).all()
        last_interaction = user_data['last_interaction']
        today = datetime.utcnow().date()

        if last_interaction:
            last_interaction_date = datetime.strptime(last_interaction, '%Y-%m-%d').date()
            if today - last_interaction_date > timedelta(days=1):
                # Apply penalty if the user missed a day
                new_training_level = max(1, user_data['training_level'] - 20)
                new_nutrition_level = max(1, user_data['nutrition_level'] - 20)
                await self.config.user(user).training_level.set(new_training_level)
                await self.config.user(user).nutrition_level.set(new_nutrition_level)
                await user.send("You've lost 20 points in both training and nutrition levels due to inactivity.")

        # Update the user's config for today
        await self.config.user(user).last_interaction.set(today.strftime('%Y-%m-%d'))
        await self.config.user(user).last_command_used.set(command_used)

        # Increment specific stats based on the command used
        if command_used == "train":
            new_training_level = user_data['training_level'] + 10
            await self.config.user(user).training_level.set(new_training_level)
        elif command_used == "diet":
            new_nutrition_level = user_data['nutrition_level'] + 10
            await self.config.user(user).nutrition_level.set(new_nutrition_level)

async def setup(bot):
    await bot.add_cog(Bullshido(bot))
