from sqlalchemy import Column, Integer, String, Float, DateTime
from . import MCDeclarativeBase


class ServerStatus(MCDeclarativeBase):
    """
    Definition of server_status table.

    hostname: name of server (String). Part of primary_key
    mc_time: time report received by M&C (DateTime). Part of primary_key
    ip_address: IP address of server (String)
    system_time: time report sent by server (DateTime)
    num_cores: number of cores on server (Integer)
    cpu_load_pct: CPU load percent = total load / num_cores, 5 min average (Float)
    uptime_days: server uptime in decimal days (Float)
    memory_used_pct: Percent of memory used, 5 min average (Float)
    memory_size_gb: Amount of memory on server in GB (Float)
    disk_space_pct: Percent of disk used (Float)
    disk_size_gb: Amount of disk space on server in GB (Float)
    network_bandwidth_mbs: Network bandwidth in MB/s. Can be null if not applicable
    """
    __tablename__ = 'server_status'
    hostname = Column(String(32), primary_key=True)
    mc_time = Column(DateTime(timezone=True), primary_key=True)
    ip_address = Column(String(32), nullable=False)
    system_time = Column(DateTime(timezone=True), nullable=False)
    num_cores = Column(Integer, nullable=False)
    cpu_load_pct = Column(Float, nullable=False)
    uptime_days = Column(Float, nullable=False)
    memory_used_pct = Column(Float, nullable=False)
    memory_size_gb = Column(Float, nullable=False)
    disk_space_pct = Column(Float, nullable=False)
    disk_size_gb = Column(Float, nullable=False)
    network_bandwidth_mbs = Column(Float)

    def __repr__(self):
        return ("<ServerStatus('{self.hostname}', '{self.mc_time}', "
                "'{self.ip_address}', '{self.system_time}, '{self.num_cores}'"
                "'{self.cpu_load_pct}', '{self.uptime_days}, '{self.memory_used_pct}'"
                "'{self.memory_size_gb}', '{self.disk_space_pct}'"
                "'{self.disk_size_gb}', '{self.network_bandwidth_mbs}')>".format(
                    self=self))

    def __eq__(self, other):
        if isinstance(other, ServerStatus):
            self_columns = [a for a in dir(self) if not a.startswith('__') and
                            isinstance(a, Column)]
            other_columns = [a for a in dir(other) if not a.startswith('__') and
                             isinstance(a, Column)]
            if set(self_columns) != set(other_columns):
                print('Sets of columns do not match. Left is {lset},'
                      ' right is {rset}'.format(lset=self_columns,
                                                rset=other_columns))
                return False

            c_equal = True
            for c in self_columns:
                self_c = getattr(self, c)
                other_c = getattr(other, c)
                if self_c != other_c:
                    c_equal = False
            return c_equal
        else:
            print('Classes do not match')
            return False
