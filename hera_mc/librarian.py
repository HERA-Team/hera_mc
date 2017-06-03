# -*- mode: python; coding: utf-8 -*-
# Copyright 2016 the HERA Collaboration
# Licensed under the 2-clause BSD license.

"""Librarian tables

"""
from astropy.time import Time
from sqlalchemy import Column, ForeignKey, Integer, BigInteger, String, Text, Float
from . import MCDeclarativeBase


class LibStatus(MCDeclarativeBase):
    """
    Definition of lib_status table.

    time: time of this status in gps seconds (double). Primary_key
    num_files: number of files in librarian (BigInteger)
    data_volume_gb: data volume in GB (Float)
    free_space_gb: free space in GB (Float)
    upload_min_elapsed: minutes elapsed since last file upload (Float)
    num_processes: number of background tasks running (Integer)
    git_version: librarian git version (String)
    git_hash: librarian git hash (String)
    """
    __tablename__ = 'lib_status'
    time = Column(Float, primary_key=True)
    num_files = Column(Integer, nullable=False)
    data_volume_gb = Column(Float, nullable=False)
    free_space_gb = Column(Float, nullable=False)
    upload_min_elapsed = Column(Float, nullable=False)
    num_processes = Column(Integer, nullable=False)
    git_version = Column(String(32), nullable=False)
    git_hash = Column(String(64), nullable=False)

    tols = {'time': {'atol': 1e-3, 'rtol': 0},
            'data_volume_gb': {'atol': 1e-3, 'rtol': 0},
            'free_space_gb': {'atol': 1e-3, 'rtol': 0},
            'upload_min_elapsed': {'atol': 1e-3 * 60, 'rtol': 0}}

    @classmethod
    def new_status(cls, time, num_files, data_volume_gb, free_space_gb,
                   upload_min_elapsed, num_processes, git_version, git_hash):
        """
        Create a new lib_status object.

        Parameters:
        ------------
        time: astropy time object
            time of this status
        num_files: integer
            number of files in librarian
        data_volume_gb: float
            data volume in GB
        free_space_gb: float
            free space in GB
        upload_min_elapsed: float
            minutes since last file upload
        num_processes: integer
            number of background tasks running
        git_version: string
            Librarian git version
        git_hash: string
            Librarian git hash
        """
        if not isinstance(time, Time):
            raise ValueError('time must be an astropy Time object')
        time = time.utc.gps

        return cls(time=time, num_files=num_files, data_volume_gb=data_volume_gb,
                   free_space_gb=free_space_gb, upload_min_elapsed=upload_min_elapsed,
                   num_processes=num_processes, git_version=git_version,
                   git_hash=git_hash)
