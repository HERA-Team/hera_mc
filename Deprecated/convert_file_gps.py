from astropy.time import Time
import math

convert_parts_paper = True
if convert_parts_paper:
    fpin = open('initialization_data_parts_paper_datetime.csv','r')
    fout = open('initialization_data_parts_paper.csv','w')

    firstLine=True
    for line in fpin:
        data = line.split(",")
        if not firstLine and len(data)>1:
            data[4] = '%.0f' % math.floor(Time(data[4]).gps)
            try:
                data[5] = '%.0f' % math.floor(Time(data[5]).gps)
            except ValueError:
                data[5] = ''
            s = ''
            for d in data:
                s+=(d+',')
            fout.write(s[:-1]+'\n')
        else:
            fout.write(line.strip()+'\n')
            firstLine = False

convert_connections = False
if convert_connections:
    fpin = open('initialization_data_connections_datetime.csv','r')
    fout = open('initialization_data_connections.csv','w')

    firstLine=True
    for line in fpin:
        data = line.split(",")
        if not firstLine and len(data)>1:
            data[6] = '%.0f' % math.floor(Time(data[6]).gps)
            try:
                data[7] = '%.0f' % math.floor(Time(data[7]).gps)
            except ValueError:
                data[7] = ''
            s = ''
            for d in data:
                s+=(d+',')
            fout.write(s[:-1]+'\n')
        else:
            fout.write(line.strip()+'\n')
            firstLine = False

convert_geo_location = False
if convert_geo_location:
    fpin = open('initialization_data_geo_location_datetime.csv','r')
    fout = open('initialization_data_geo_location.csv','w')

    firstLine=True
    for line in fpin:
        data = line.split(",")
        if not firstLine and len(data)>1:
            data[7] = '%.0f' % math.floor(Time(data[7]).gps)
            s = ''
            for d in data:
                s+=(d+',')
            s = s.strip(',')
            fout.write(s+'\n')
        else:
            fout.write(line.strip()+'\n')
            firstLine = False