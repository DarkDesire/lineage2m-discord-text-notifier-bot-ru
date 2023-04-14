import timedelta
from datetime import datetime as dt
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
import typing

Base = declarative_base()

engine = create_engine("sqlite:///./utils/database.sqlite3")
Session = sessionmaker(bind=engine)
session = Session()

class Boss(Base):
    __tablename__ = "bosses"
    
    region = Column(String) #0
    origin_boss_name = Column(String) #1
    chance = Column(Integer) #2
    respawn_hours = Column(Integer) #3
    name = Column(String, primary_key=True) #4
    location_name = Column(String) #5
    resp_timestamp = Column(String) #6
    
    full_date_pattern = "%Y-%m-%d %H:%M"
    date_pattern = "%Y-%m-%d"
    date_pattern_regex = "(\d{4}-\d{2}-\d{2})"
    
    time_pattern = "%H:%M"
    time_pattern_regex = "(\d{2}:\d{2})"
    
    def __init__(self, region, origin_boss_name, 
                 chance, respawn_hours, name, 
                 location_name, resp_timestamp = None):
        self.region = region
        self.origin_boss_name = origin_boss_name
        self.chance = chance
        self.respawn_hours = respawn_hours
        self.name = name
        self.location_name = location_name
        self.resp_timestamp = resp_timestamp
        self.sound_5min = "_".join([self.origin_boss_name.lower().replace(" ","-"),"5min"])
        self.sound_appear = "_".join([self.origin_boss_name.lower().replace(" ","-"),"appear"])

    
    ############### Object Methods ################################

    def _dt_from_string(self) -> dt:
        return dt.strptime(self.resp_timestamp, self.full_date_pattern)
    
    def commit(self):
        session.commit()
    
    def set_resp_timestamp(self, killed_dt: dt = None, manual: bool = True): 
        # manual - means it's from command, manual = True
        # manual = False, scheduled 
        
        if killed_dt is None and manual:
            self.resp_timestamp = None
            return
        
        if manual:
            next_dt = killed_dt
            while (next_dt < dt.now()):
                next_dt = next_dt + timedelta.Timedelta(hours=self.respawn_hours)
        else:
            next_dt = self._dt_from_string() + timedelta.Timedelta(hours=self.respawn_hours)
            
        self.resp_timestamp = next_dt.strftime(self.full_date_pattern)
        
    def auto_tagged(self):
        curr_resp_dt = self._dt_from_string() 
        next_dt = curr_resp_dt + timedelta.Timedelta(hours=self.respawn_hours)
        return(f"{curr_resp_dt.strftime(self.time_pattern)} мск | **{self.name.upper()}** появился. След респ через {self.respawn_hours}ч в {next_dt.strftime(self.time_pattern)} мск")
    
    def boss_untagged_str(self) -> str:
        return(f"Босс **{self.name.upper()}** удален из списка!")
               
    def boss_tagged_str(self) -> str:
        (hours, minutes, _) = self.last_time()
        return(f"Босс **{self.name.upper()}** убит!\nЯ напомню о его респе через {hours}ч {minutes}м")

    def boss_status_str(self):
        if self.resp_timestamp is None:
            return(f"**{self.name.upper()}** не залоган")
        
        (hours, minutes, is_valid) = self.last_time()
        
        hours_minutes = self._dt_from_string().strftime(self.time_pattern)
        
        if hours == 0 and minutes == 0 or not is_valid:
            return(f"{hours_minutes} мск | **{self.name.upper()}** в __{self.location_name}__ появился! | {self.chance}%")
        elif is_valid:
            return(f"{hours_minutes} мск | **{self.name.upper()}** в __{self.location_name}__ через {hours}ч {minutes}м | {self.chance}%")
        else: 
            pass
            

    def last_time(self):
        try:
            duration =  timedelta.Timedelta(self._dt_from_string() - dt.now()) + timedelta.Timedelta(minutes=1)
            is_valid = self._dt_from_string() > dt.now()
            days, seconds = duration.days, duration.seconds
            hours = days * 24 + seconds // 3600
            minutes = (seconds % 3600) // 60
            return (hours, minutes, is_valid)
        except: 
            return (0, 0, False)
    
    ############### Class Methods #################################
    
    @classmethod
    def request_bosses_names_without_resp(cls):
        bosses = (session.query(Boss.name)
                  .filter(Boss.resp_timestamp.is_(None))
                  .order_by(Boss.name.asc())
                  .all())
        bosses_names = list(map(lambda x: x[0], bosses))
        return bosses_names
    
    @classmethod
    def request_bosses_names(cls) -> typing.List[str]:
        bosses = (session.query(Boss.name)
                  .order_by(Boss.name.asc()).all())
        bosses_names = list(map(lambda x: x[0], bosses))
        return bosses_names
    
    @classmethod
    def request_boss_by_name_startswith(cls, name):
        bosses = (session.query(Boss)
                  .filter(Boss.name.startswith(name.lower())).all())
        if len(bosses) > 1:
            raise ManyBossesReturned(name, list(map(lambda x: x.name.lower(), bosses)))
        if len(bosses) == 0:
            raise NoBossFound(name)

        return bosses[0]
    
    @classmethod
    def request_bosses_by_region(cls, region: str):
        bosses = (session.query(Boss)
                 .filter(Boss.region.is_(region))
                 .order_by(Boss.resp_timestamp.asc())
                 .all())
        return bosses
    
    @classmethod
    def request_bosses_by_close_resp_timestamp(cls, limit: int = None):
        bosses = (session.query(Boss)
                 .filter(Boss.resp_timestamp.is_not(None))
                 .order_by(Boss.resp_timestamp.asc())
                 .limit(limit).all())
        return bosses
            
    @classmethod
    def request_reset_bosses_resp_timestamp(cls):
        bosses = session.query(Boss).all()
        [boss.set_resp_timestamp(None) for boss in bosses]
        session.commit()
        
############## User-defined exceptions ##############

class NoBossFound(Exception):
    def __init__(self, name: str, message: str="Нет боссов с таким именем"):
        self.name = name
        self.message = message
        super().__init__(self.message)

class ManyBossesReturned(Exception):
    def __init__(self, name: str, bosses: typing.List[str], message: str="Найдено больше 1 босса"):
        self.name = name
        self.bosses = bosses
        self.message = message
        super().__init__(self.message)