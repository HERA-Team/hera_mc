from sqlalchemy import Column, Integer, String, Float, DateTime
from . import MCDeclarativeBase


class RTPStatus(MCDeclarativeBase):
    """
    Definition of rtp_status table.

    time: time of this status (DateTime). Primary_key
    status: status (options TBD) (String)
    event_min_elapsed: minutes elapsed since last event (Float)
    num_processes: number of processes on running (Integer)
    restart_hours_elapsed: hours elapsed since last restart (Float)
    """
    __tablename__ = 'rtp_status'
    time = Column(DateTime(timezone=True), primary_key=True)
    status = Column(String(64), nullable=False)
    event_min_elapsed = Column(Float, nullable=False)
    num_processes = Column(Integer, nullable=False)
    restart_hours_elapsed = Column(Float, nullable=False)

    @classmethod
    def new_status(cls, time, status, event_min_elapsed, num_processes,
                   restart_hours_elapsed):
        """
        Create a new rtp_status object.

        Parameters:
        ------------
        time: datetime
            time of this status
        status: string
            status (options TBD)
        event_min_elapsed: float
            minutes since last event
        num_processes: integer
            number of processes running
        restart_hours_elapsed: float
            hours since last restart
        """

        return cls(time=time, status=status, event_min_elapsed=event_min_elapsed,
                   num_processes=num_processes, restart_hours_elapsed=restart_hours_elapsed)
