import re
import asyncio
from utils.boss import Boss, ManyBossesReturned, NoBossFound
from utils.extended_client import ExtendedClient
from datetime import datetime as dt

class TextBotClient(ExtendedClient):
    
    async def on_message(self, message) -> None:
        ## Checking that message is not from bot
        ## Checking that channel is equal to required channel
        if message.author == self.user or message.channel.name != self.required_channel:
            return
        ## Cleaning the command
        command = message.content.lower().strip()
        
        simple_commands = {
            '?': self.boss_names,
            '??': self.not_logged_boss_names,
            '!': self.show_n,
            '!гиран': lambda: self.show_by_region(region='Giran'),
            '!орен': lambda: self.show_by_region(region='Oren'),
            '!аден': lambda: self.show_by_region(region='Aden'),
            '!беора': lambda: self.show_by_region(region='Veora'),
            '!рестарт': self.reset_all,
            'help': self.command_not_found,
        }
        
        if command in simple_commands:
            await simple_commands[command]()
        elif command.startswith("!"):
            try:
                await self.show_n(int(command[1:]))
            except:
                await self.command_not_found()
        elif command.startswith('-'):
            await self.delete_boss_handler(command)
        elif command.startswith('+'):
            await self.add_boss_handler(command)
        else:
            await self.command_not_found()
            
    ########################## Methods  ############################

    async def boss_untagged(self, boss_name:str) -> None:
        await self.channel.send(f"Босс **{boss_name}** был исключен из списка.")

    async def show_n(self, n: int = None) -> None:
        bosses = Boss.request_bosses_by_close_resp_timestamp(n)
        if not bosses:
            await self.channel.send("Нет залоганных боссов!")
            return

        await self.send_bosses_as_messages(bosses, n)
                
    async def show_by_region(self, region: str) -> None:
        bosses = Boss.request_bosses_by_region(region)
        await self.send_bosses_as_messages(bosses)
        
    async def send_bosses_as_messages(self, bosses, n:int = None) -> None:
        all_bosses_str = [boss.boss_status_str() for boss in bosses][:n]
        len_bosses = len(all_bosses_str)
        if len_bosses > 3:
            first_msg = "\n".join(all_bosses_str[:len_bosses//2])
            second_msg = "\n".join(all_bosses_str[len_bosses//2:])
            if first_msg:
                await self.channel.send(first_msg)
            if second_msg:
                await self.channel.send(second_msg)
        else:
            await self.channel.send("\n".join(all_bosses_str))
            
    async def reset_all(self) -> None:
        Boss.request_reset_bosses_resp_timestamp()
        msg = "Боссы удалены из списка"
        await self.channel.send(msg)
        
    async def not_logged_boss_names(self) -> None:
        bossess_names = Boss.request_bosses_names_without_resp() 
        msg1 = "Незалоганные боссы: \n"
        msg2 = ", ".join([self.bold(boss_name) for boss_name in bossess_names])
        
        await self.channel.send(msg1+msg2)
        
    async def boss_names(self) -> None:
        bossess_names = Boss.request_bosses_names()
        msg = ", ".join([self.bold(boss_name) for boss_name in bossess_names])
        await self.channel.send(msg)
    
    async def parser_date_helper(self, date: str, pattern: str) -> dt:
        try:
            return dt.strptime(date, pattern)
        except ValueError:
            await self.channel.send(f'Invalid format: {date} | Expected pattern: {pattern}')
    
    async def add_boss_handler(self, text: str) -> None:
        pattern =  rf'^\+(\w+)(?:\s+{Boss.date_pattern_regex})?(?:\s+{Boss.time_pattern_regex})?$'
        # Example, +breka 2023-04-13 10:53 -> ("breka", "2023-04-13", "10:53")
        # Example, +breka 10:53 -> ("breka", "2023-04-13", None) 
        # Example, +breka -> ("breka", None, None) 
        
        match = re.match(pattern, text)
        killed_dt = None
        
        if match:
            name, date, time = match.groups()
            if time:
                time = await self.parser_date_helper(time, Boss.time_pattern)
            if date:
                date = await self.parser_date_helper(date, Boss.date_pattern)
                
            if date and time: # full date, ex. 2022-01-29 05:10
                killed_dt = date.replace(hour=time.hour, minute=time.minute, second=0)
            elif time:  # short time, ex. 05:10 -> (today) 05:10
                killed_dt = dt.now().replace(hour=time.hour, minute=time.minute, second=0)
            else: # no time and date -> (today)
                killed_dt = dt.now().replace(second=0)

            await self.add_boss(name, killed_dt)
        else:
            await self.command_not_found()
                
    async def add_boss(self, name: str, killed_dt: dt) -> None:
        try:
            boss = Boss.request_boss_by_name_startswith(name)
            boss.set_resp_timestamp(killed_dt, manual=True)
            boss.commit()
            await self.channel.send(boss.boss_tagged_str())
        except ManyBossesReturned as error:
            bosses = error.bosses
            bosses_str = ", ".join(bosses)
            await self.channel.send(f"[{error.name}] | Возможно вы хотели добавить: {bosses_str}")
        except NoBossFound as error:
            await self.channel.send(f"[{error.name}] | Босс не найден")
    
    async def delete_boss_handler(self, text: str) -> None:
        parts = text[1:].split()
        if len(parts) == 1:
            boss_name = parts[0]
            await self.delete_boss(boss_name)
        else:
            await self.command_not_found()
        
    async def delete_boss(self, name: str) -> None:
        try:
            boss = Boss.request_boss_by_name_startswith(name)
            boss.set_resp_timestamp(None, manual=True)
            boss.commit()
            await self.channel.send(boss.boss_untagged_str())
        except ManyBossesReturned as error:
            bosses = error.bosses
            bosses = ", ".join(bosses)
            await self.channel.send(f"[{error.name}] | Возможно вы хотели удалить: {bosses}")
        except NoBossFound as error:
            await self.channel.send(f"[{error.name}] | Босс не найден")

    async def command_not_found(self) -> None:
        header = self.bold("Доступные команды:")
        show_all = self.bold("!") + " (список залоганных боссов)"
        show_n = self.bold("!N") + " (список залоганных первых N боссов)"
        show_oren = self.bold("!орен") + " (список всех боссов Орен)"
        show_aden = self.bold("!аден") + " (список всех боссов Аден)"
        show_veora = self.bold("!беора") + " (список всех боссов Беора)"
        reset_all = self.bold("!рестарт") + " (удаляет время респа всех боссов)"
        boss_names = self.bold("?") + " (список имен всех боссов)"
        not_logged_boss_names = self.bold("??") + " (список имен незалоганных боссов)"
        add_boss = self.bold("+босс") + " (добавляет босса, убили сейчас)"
        add_boss_short_time = self.bold("+босс 10:53") + " (добавляет босса, убили сегодня, в опр время)"
        add_boss_full_time = self.bold("+босс 2023-04-12 10:53") + " (добавляет босса, убили в опр день и время)"
        delete_boss = self.bold("-босс") +" (удаляет время респа босса)"
        help_msg = self.bold("help") + " (вызывать эту подсказку)"
        msg = "\n".join([header,show_all,show_n,show_oren, show_aden, show_veora, reset_all, 
                         boss_names,not_logged_boss_names,
                         add_boss,add_boss_short_time,add_boss_full_time,
                         delete_boss,help_msg])
        await self.channel.send(msg)
    
    ########################## Background task ############################

    # Task runs every 5min = 300 seconds
    async def bg_notification_task(self) -> None:
        await self.wait_until_ready()
        self.set_channel(voice=False) ## attaching to the text channel
        
        while not self.is_closed():
            await self.notification()
            await asyncio.sleep(300)
            
    async def notification(self):
        bosses = Boss.request_bosses_by_close_resp_timestamp(20)
        if len(bosses) > 0:
            soon_bosses = []
            delete_bosses = []
            
            for boss in bosses:
                (hours, minutes, is_valid) = boss.last_time()
                if not is_valid:
                    delete_bosses.append(boss)
                elif is_valid and hours == 0 and minutes <= 5:
                    soon_bosses.append(boss)
                else:
                    pass
                
            result_msg = ''
            if len(delete_bosses)>0:
                deleted_header = "@here\nНеотмеченные боссы:\n"
                msg = "\n".join([boss.auto_tagged() for boss in delete_bosses])
                result_msg = result_msg + '\n' + deleted_header + msg + '\n'
                for boss in delete_bosses:
                    boss.set_resp_timestamp(manual = False)
                    boss.commit()
                
            if len(soon_bosses)>0:
                closed_header = "@here\nБоссы ближайшие 5 минут:\n"
                msg = "\n".join([boss.boss_status_str() for boss in soon_bosses])
                result_msg = result_msg + closed_header + msg

            if result_msg:
                await self.channel.send(result_msg)
                
    ###########################################################################