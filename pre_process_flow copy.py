import pandas as pd
import os
import requests
import textract
import numpy as np

API_KEY = "AIzaSyB8rJhDsfwvIod9jVTfFm1Dtv2eO4QWqxQ"
GOOGLE_MAPS_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Years that have parsers
PARSEABLE_YEARS = [2013, 2017, 2019]

"""
New generic method to process ADT data into csv files
"""
def process_adt_data(year):
    print("Processing %d ADT data" % year)

    # create output folder if it doesn't already exist
    output_folder = "%d processed/" % year
    if not os.path.isdir(os.getcwd() + "/" + output_folder):
        os.mkdir(os.getcwd() + output_folder)

    # parse excel files by iterating over them
    input_folder = "%d ADT Data/" % year
    input_files = os.listdir(os.getcwd() + "/" + input_folder)
    # keep track of main road info while parsing files (to get geo coord. later)
    cache_main_roads = []
    for file_name in input_files:
        if is_excel_file(file_name):
            print("parsing:", file_name)
            xls_file = pd.ExcelFile(input_folder + file_name)
            dfs = {}
            for sheet_name in xls_file.sheet_names:
                dfs[sheet_name] = xls_file.parse(sheet_name)

            input_bis, main_road_info = None, None
            if year == 2013:
                input_bis, main_road_info = parse_excel_2013(dfs, file_name)
            elif year == 2017:
                input_bis = parse_excel_2017(dfs)
            elif year == 2019:
                input_bis = parse_excel_2019(dfs)
            else:
                raise(Exception("Unknown excel file format for year %d, "
                      "create a parser or edit code to accept it "
                      "if it has the same format of another year" % year))

            # write parsed results to csv file
            input_bis.to_csv(output_folder + remove_ext(file_name) + ".csv")
            if main_road_info:
                cache_main_roads.append(main_road_info)

    # if main road info is not available from the data in the files,
    # get the  main road info from the file name by parsing.
    # For example, 2013 files have road info inside the files
    # but 2017 and 2019 files do not so we get them from their file name
    if not cache_main_roads:
        for file_name in input_files:
            if is_valid_file(file_name):
                main_road_info = None
                if year == 2017:
                    main_road_info = get_main_road_info_2017(file_name)
                elif year == 2019:
                    main_road_info = get_main_road_info_2019(file_name)
                else:
                    raise(Exception('Unable to get main road info for file: %s' % file_name))

                cache_main_roads.append(main_road_info)

    # get geo coordinates using google API and cache_main_roads
    # write the results in the csv file, 'year_info_coor.csv'
    coordinate_file = open('%d_info_coor.csv' % year, 'w')
    coordinate_file.write("Name,City,Main road,Cross road,Start lat,Start lng,End lat,End lng\n")
    for main_road_info in cache_main_roads:
        # print('main info:', main_road_info)
        file_name, city, main_road, cross_road, cross1, cross2 = main_road_info
        if cross1 and cross2:
            lat1, lng1 = get_coords_from_address(main_road + ' & ' + cross1 + ', ' + city)
            lat2, lng2 = get_coords_from_address(main_road + ' & ' + cross2 + ', ' + city)
            line = file_name + ',' + city + ',' + main_road + ',' + cross_road + ',' + \
                   str(lat1) + ',' + str(lng1) + ',' + str(lat2) + ',' + str(lng2) + '\n'
            coordinate_file.write(line)
        elif cross1:
            lat, lng = get_coords_from_address(main_road + ' & ' + cross1 + ', ' + city)
            line = file_name + ',' + city + ',' + main_road + ',' + cross_road + ',' + \
                   str(lat) + ',' + str(lng) + '\n'
            coordinate_file.write(line)
        else:
            raise(Exception('Unable to get coordinates for main road of file %s' % file_name))

    coordinate_file.close()

"""
Get 2017 main road info from file name
input: file_name, examples below 
file_name = mission blvd BT driscoll rd AND I 680 NB
file_name = mission blvd S OF washington blvd signal
output = (file_name, city, main_road, cross_road, cross1, cross2)
"""
def get_main_road_info_2017(file_name):
    name = remove_ext(file_name).title()
    city = 'Fremont'
    main_road_info = None
    if 'Bt' in name:
        # Ex1: mission blvd BT driscoll rd AND I 680 NB
        main_road = name.split('Bt')[0].strip()
        cross_road = name.split('Bt')[1].strip()
        cross1 = remove_direction(cross_road.split('And')[0]).strip()
        cross2 = remove_direction(cross_road.split('And')[1]).strip()
        main_road_info = (file_name, city, main_road, cross_road, cross1, cross2)
    elif get_of_direction(name):
        # Ex2: mission blvd S OF washington blvd signal
        of_direction = get_of_direction(name)  # S OF
        main_road = name.split(of_direction)[0].strip()
        cross_road = name.split(of_direction)[1] \
            .replace('Signal', '') \
            .replace('Stop Sign', '') \
            .strip()
        cross1 = remove_direction(cross_road)
        main_road_info = (file_name, city, main_road, cross_road, cross1, None)
    else:
        raise(Exception('Unable to parse main road info from 2017 file name: %s' % file_name))

    return main_road_info

"""
Get 2019 main road info from file name
input: file_name, examples below 
file_name = Driscoll Rd Bet. Mission Blvd & Paseo Padre Pkwy
file_name = AUTO MALL PKWY BT FREMONT BLVD AND I-680 EB
output = (file_name, city, main_road, cross_road, cross1, cross2)
"""
def get_main_road_info_2019(file_name):
    name = remove_ext(file_name).title()
    city = 'Fremont'

    bt = find_splitter(name, ['Bt', 'Bet.'])
    main_road = name.split(bt)[0].strip()
    cross_road = name.split(bt)[1].strip()

    And = find_splitter(cross_road, ['And', '&'])
    cross1 = remove_direction(cross_road).split(And)[0].strip()
    cross2 = remove_direction(cross_road).split(And)[1].strip()

    main_road_info = (file_name, city, main_road, cross_road, cross1, cross2)
    return main_road_info


def parse_excel_2013(dfs, file_name):
    # for ease of parsing
    Input = dfs['Input']
    Input.to_csv("test_tmp.csv")

    # get main road info
    city = Input.columns[7]
    main_road = Input[city][0]
    cross_road = Input[city][1]
    city = city.split(",")[0]  # Fremont, CA -> Fremont
    cross1, cross2 = get_cross_roads_2013(cross_road)
    main_road_info = (file_name, city, main_road, cross_road, cross1, cross2)

    # read to csv directly and select columns
    Input_bis = pd.read_csv("test_tmp.csv", skiprows=4)
    Input_bis = Input_bis[['Unnamed: 1', 'TIME', 'NB', 'SB', 'EB', 'WB']]
    Input_bis = Input_bis.rename(columns={'Unnamed: 1': 'Date'})

    return Input_bis, main_road_info

def get_cross_roads_2013(cross):
    cross1, cross2 = None, None
    if 'Between' in cross:
        # example: Between Arapaho and Paseo Padre
        cross = cross.replace('Between', '').strip()
        cross1 = cross.split('and')[0].strip()
        cross2 = cross.split('and')[1].strip()
    else:
        # example: 200' s/o Starlite -> Starlite
        cross1 = cross[9:]
    return cross1, cross2


def parse_excel_2017(dfs):
    # for ease of parsing
    Input = dfs['Sheet1']
    Input.to_csv("test_tmp.csv")
    Input_bis = pd.read_csv("test_tmp.csv", skiprows=6)

    # drop useless col
    Input_bis = Input_bis.drop(['5'], axis=1)
    return Input_bis


def remove_direction(string):
    return string.replace('Nb', '').replace('Sb', '')\
        .replace('Eb', '').replace('Wb', '')


def get_of_direction(string):
    of_directions = ['S Of', 'E Of', 'W Of', 'N Of']
    for of in of_directions:
        if of in string:
            return of

def find_splitter(string, splitters):
    for splitter in splitters:
        if splitter in string:
            return splitter

def parse_excel_2019(dfs):
    # parse the excel sheets and concatenate their data
    Input1 = parse_sheet_helper_2019('Day 1', dfs)
    Input2 = parse_sheet_helper_2019('Day 2', dfs)
    Input3 = parse_sheet_helper_2019('Day 3', dfs)
    Input1 = Input1.append(Input2, ignore_index=True)
    Input1 = Input1.append(Input3, ignore_index=True)

    # rename columns accordingly
    # (matching was done visually printing the data frames and matching to xls data)
    # print(Input1)
    Input1 = Input1.rename(columns={'date': 'Date', 'Unnamed: 25': 'Time',
                                    'Unnamed: 26': 'NB', 'Unnamed: 27': 'SB',
                                    'Unnamed: 28': 'EB', 'Unnamed: 29': 'WB'})
    return Input1


"""
Todo: We may improve this by opening the excel file once and not
creating a temp file
Process 2013 ADT data into csv files
"""
#edson1
def process2013_adt_data():
    print("Processing 2013 ADT data")
    # Create fs file to track the files that were processed
    fs = open("2013_info.csv", "w")
    fs.write("File name,City,On street,Cross street\n")

    # create processed folder if not already present
    processed_folder = os.getcwd() + "/2013 processed/"
    if not os.path.isdir(processed_folder):
        os.mkdir(processed_folder)

    # iterate over excel files to process them
    cwd = os.getcwd()
    for l in os.listdir(cwd + "/2013 ADT Data"):
        if is_excel_file(l):
            # read excel file and write test_tmp.csv for ease of parsing
            xl_file = pd.ExcelFile("2013 ADT Data/" + l)
            dfs = {sheet_name: xl_file.parse(sheet_name)
                   for sheet_name in xl_file.sheet_names}
            # Edson: iterate over sheet names and get an idea of how
            # the dfs[Input] data looks like
            # then try to get the city, road and cross data
            # then create csv with desired data as shown below
            Input = dfs['Input']
            Input.to_csv("test_tmp.csv")

            # get city, road, cross info from test_tmp.csv file
            f = open("test_tmp.csv", "r")
            city = (f.readline().split(",")[8]).replace('\"', '')
            road = (f.readline().split(",")[8]).replace('\"', '')
            cross = (f.readline().split(",")[8]).replace('\"', '')
            print((city, road, cross))
            fs.write(l + "," + city + "," + road + "," + cross + "\n")
            f.close()

            # write parsed data to csv and put in 2013 processed folder
            Input_bis = pd.read_csv("test_tmp.csv", skiprows=4)
            Input_bis = Input_bis[['Unnamed: 1', 'TIME', 'NB', 'SB', 'EB', 'WB']]
            Input_bis.to_csv("2013 processed/" + l.split('.x')[0] + ".csv")
        else:
            print("skipping non excel file/dir: ", l)

    fs.close()

"""
Todo: create a 2017_info.csv in the same fashion as the 2013_info.csv file
- Same notes as 2013, creates temp file, we could try to parse without it
- Process 2017 ADT data into csv files
- 2017 data lacks NB and SB data columns
"""
def process2017_adt_data():
    print("Processing 2017 ADT data")
    # create processed folder if not already present
    processed_folder = os.getcwd() + "/2017 processed/"
    if not os.path.isdir(processed_folder):
        os.mkdir(processed_folder)

    for l in os.listdir("2017 ADT Data"):
        if is_excel_file(l):
            print(l)
            xl_file = pd.ExcelFile("2017 ADT Data/" + l)
            dfs = {sheet_name: xl_file.parse(sheet_name)
                   for sheet_name in xl_file.sheet_names}
            Input = dfs['Sheet1']
            Input.to_csv("test_tmp.csv")

            Input_bis = pd.read_csv("test_tmp.csv", skiprows=6)
            Input_bis = Input_bis.rename(columns=lambda s: title_helper_2017(s))
            # HERE I MIGHT WANT TO CHANGE THAT
            print(Input_bis.columns)
            Input_bis = Input_bis.drop(['5'], axis=1)
            Input_bis.to_csv("2017 processed/" + l.split('.x')[0] + ".csv")

"""
Process 2019 ADT data into csv files
"""
def process2019_adt_data():
    print("Processing 2019 ADT data")
    # create processed folder if not already present
    processed_folder = os.getcwd() + "/2019 processed/"
    if not os.path.isdir(processed_folder):
        os.mkdir(processed_folder)

    cwd = os.getcwd()
    for l in os.listdir(cwd + "/2019 ADT Data"):
        if is_excel_file(l):
            print(l)
            xl_file = pd.ExcelFile("2019 ADT Data/" + l)
            dfs = {sheet_name: xl_file.parse(sheet_name)
                   for sheet_name in xl_file.sheet_names}
            # print(dfs.keys())
            Input1 = parse_sheet_helper_2019('Day 1', dfs)
            Input2 = parse_sheet_helper_2019('Day 2', dfs)
            Input3 = parse_sheet_helper_2019('Day 3', dfs)
            Input1 = Input1.append(Input2, ignore_index=True)
            Input1 = Input1.append(Input3, ignore_index=True)
            Input1.to_csv("2019 processed/" + l.split('.x')[0] + ".csv", header=['TIME', 'NB', 'SB', 'EB', 'WB', 'date'])


def parse_sheet_helper_2019(name, dfs):
    Input = dfs[name]
    day = Input.iloc(1)[1][3]
    #     print(day)
    col = Input.columns
    Input = Input.drop(col[:25], axis=1)
    Input = Input.drop(col[30:], axis=1)
    Input = Input.drop(Input.index[[i for i in range(9)]])
    Input = Input.assign(date=day)
    return Input

def title_helper_2017(s):
    if "NB" in s:
        return 'NB'
    if "EB" in s:
        return 'EB'
    if "SB" in s:
        return 'SB'
    if "WB" in s:
        return 'WB'
        #     if "NB" in s or "EB" in s:
        #         return 'Way 1 (NB - EB)'
        #     if "SB" in s or "WB" in s:
        #         return 'Way 2 (SB - WB)'
    return s

def is_excel_file(file_name):
    _, file_ext = os.path.splitext(file_name)
    return (file_ext == '.xls' or file_ext == '.xlsx') and is_valid_file(file_name)

def is_valid_file(file_name):
    is_folder = os.path.isdir(os.getcwd() + '/' + file_name)
    return '$' not in file_name and '.DS_Store' not in file_name and not is_folder


def remove_ext(file_path):
    file_name, _ = os.path.splitext(file_path)
    return file_name

"""
Code for finding the coordinates of the city detectors and give one csv file 
with the location of the detectors
"""
def get_geo_data2013():
    # parse street roads
    f = open('2013_info.csv', 'r')
    print(f.readline())

    # new file with same info plus coordinates (long, lat)
    w = open("2013_info_coor.csv", 'w')
    w.write("Name,City,Main road,Cross road,Start lat,Start lng,End lat,End lng\n")

    for l in f:
        # remove some tokens
        l_tmp = l.replace("\n", '')
        s_tmp = l_tmp.replace("EB ", '').replace("WB ", '').split(',')
        print(s_tmp[1:])
        city = s_tmp[1]  # fremont
        road_1 = s_tmp[2]  # on street

        # special case (Edson: find out what this case handles)
        if "Between" in s_tmp[3]:
            # cross street
            r_tmp = s_tmp[3].split('Between ')[1].split(' and ')
            lat1, lng1 = get_coords_from_address(road_1 + " & " + r_tmp[0] + ", " + city)
            lat2, lng2 = get_coords_from_address(road_1 + " & " + r_tmp[1] + ", " + city)
            print(r_tmp)
            print((lat1, lng1))
            print((lat2, lng2))
            w.write(l_tmp + ", " + str(lat1) + ", " + str(lng1) + ", " + str(lat2) + ", " + str(lng2) + "\n")
        else:
            road_2 = s_tmp[3][9:]
            print(road_1 + " & " + road_2 + ", " + city)
            lat, lng = get_coords_from_address(road_1 + " & " + road_2 + ", " + city)
            print((lat, lng))
            w.write(l_tmp + ", " + str(lat) + ", " + str(lng) + "\n")
    f.close()
    w.close()

def get_geo_data2017():
    f = open('2017_info.csv', 'r')
    print(f.readline())

    w = open("2017_info_coor.csv", 'w')
    w.write("Name,City,Main road,Cross road,Start lat,Start lng,End lat,End lng\n")

    for l in f:
        city = "Fremont"
        l_tmp1 = l.replace("\n", '')
        l_tmp = l_tmp1.split('.')[0]
        if " BT " in l_tmp:
            road_1 = l_tmp.title().split(' Bt ')[0]
            r_tmp = l_tmp.title().split(' Bt ')[1].replace(' Eb', '').replace(' Wb', '').replace(' Nb', '').replace(
                ' Sb', '').split(' And ')
            lat1, lng1 = get_coords_from_address(road_1 + " & " + r_tmp[0] + ", " + city)
            lat2, lng2 = get_coords_from_address(road_1 + " & " + r_tmp[1] + ", " + city)
            print(r_tmp)
            print((lat1, lng1))
            print((lat2, lng2))
            w.write(
                l_tmp1 + "," + city + "," + road_1 + "," + l_tmp.title().split(' Bt ')[1].replace(' Eb', '').replace(
                    ' Wb', '').replace(' Nb', '').replace(' Sb', '') + "," + str(lat1) + "," + str(lng1) + "," + str(
                    lat2) + "," + str(lng2) + "\n")
        else:
            print(l_tmp)
            if " S OF " in l_tmp:
                road_2 = l_tmp.title().split(' S Of ')[1].replace(' Signal', '')
                lat, lng = get_coords_from_address(road_1 + " & " + road_2 + ", " + city)
                print((lat, lng))
                w.write(l_tmp1 + "," + city + "," + road_1 + "," + road_2 + "," + str(lat) + "," + str(lng) + "\n")
            elif " E OF " in l_tmp:
                road_2 = l_tmp.title().split(' E Of ')[1].replace(' Signal', '').replace(' Stop Sign', '')
                lat, lng = get_coords_from_address(road_1 + " & " + road_2 + ", " + city)
                print((lat, lng))
                w.write(l_tmp1 + "," + city + "," + road_1 + "," + road_2 + "," + str(lat) + "," + str(lng) + "\n")
            elif " W OF " in l_tmp:
                road_2 = l_tmp.title().split(' W Of ')[1].replace(' Signal', '')
                lat, lng = get_coords_from_address(road_1 + " & " + road_2 + ", " + city)
                print((lat, lng))
                w.write(l_tmp1 + "," + city + "," + road_1 + "," + road_2 + "," + str(lat) + "," + str(lng) + "\n")
            else:
                print("ERROR")
                break

    f.close()
    w.close()


def get_coords_from_address(address):
    payload = {
        'address': address,
        'key': API_KEY
    }
    print('getting coordinates for: ', address)
    request = requests.get(GOOGLE_MAPS_URL, params=payload).json()
    results = request['results']

    lat = None
    lng = None

    if len(results):
        answer = results[0]
        lat = answer.get('geometry').get('location').get('lat')
        lng = answer.get('geometry').get('location').get('lng')

    return lat, lng


"""
PProcess Doc files
"""
def process2017_doc_data():
    # create output folder to put results in
    create_directory(os.getcwd(), "2017 processed")

    for l in os.listdir("2017 doc"):
        if is_doc_file(l):
            # output file w
            w = open("2017 processed/" + l.split('.')[0] + '.csv', 'w')
            w.write("Day,Time,Count\n")

            text = textract.process("2017 doc/" + l)
            text_tmp = str(text).replace('\\n', ' ')
            data = text_tmp.split('*')
            for d in data[1:]:
                # parsing data block for day d
                array = d.split('|')
                # get day
                info_day = array[0].split(',')
                # get data start idx
                for j in range(len(array)):
                    if "0000" in array[j]:
                        # print("data start idx", j)
                        break

                # gather data in data_tmp
                data_tmp = np.zeros((6, 24))
                for i in range(6):
                    data_row = [array[j + i * 26 + k] for k in range(24)]
                    data_tmp[i] = np.array(data_row)
                    # print("data_row", data_row)

                analysis = array[j + 6 * 26] # some analysis, not useful

                # write data in out file
                for i in data_tmp[0]:
                    # h = hour of the day (1 to 24hr)
                    # j*15 = minutes (1 to 59)
                    # data given in 15 min intervals
                    index = ((int)(i / 100))
                    h = str(index)
                    for j in range(4):
                        day = info_day[0] + " - " + info_day[1] + " - " + info_day[2]
                        time = h + ":" + str(j * 15)
                        count = str(data_tmp[2 + j][index])
                        w.write(day + "," + time + "," + count + "\n")

                # print("info day", info_day)
                # print("data for the day", data_tmp)
                # print("some analysis for the day", analysis)
            w.close()

def process2019_doc_data():
    # create ouput folder to put results in
    create_directory(os.getcwd(), "2019 processed")

    for l in os.listdir("2019 doc"):
        if is_doc_file(l):
            # output file w
            w = open("2019 processed/" + l.split('.')[0] + '.csv', 'w')
            w.write("Day,Time,Count\n")

            text = textract.process("2019 doc/" + l)
            text_tmp = str(text).replace('\\n', ' ')
            data = text_tmp.split('*')
            for d in data[1:]:
                # parsing data block for day d
                array = d.split('|')
                # get day
                info_day = array[0].split(',')
                # get data start idx
                for j in range(len(array)):
                    if "0000" in array[j]:
                        # print("data start idx", j)
                        break

                # gather data in data_tmp
                data_tmp = np.zeros((6, 24))
                for i in range(6):
                    data_row = [array[j + i * 26 + k] for k in range(24)]
                    # print("data_row: ", data_row)
                    data_tmp[i] = np.array(data_row)
                    # for c in range(len(data_row)):
                    #     s = data_row[c].strip()
                    #     if s:
                    #         s = s.split(' ')
                    #         for el in s:
                    #             data_tmp[i][c] = float(el.strip())



                analysis = array[j + 6 * 26] # some analysis, not useful

                # write data in out file
                for i in data_tmp[0]:
                    # h = hour of the day (1 to 24hr)
                    # j*15 = minutes (1 to 59)
                    # data given in 15 min intervals
                    index = ((int)(i / 100))
                    h = str(index)
                    for j in range(4):
                        day = info_day[0] + " - " + info_day[1] + " - " + info_day[2]
                        time = h + ":" + str(j * 15)
                        count = str(data_tmp[2 + j][index])
                        w.write(day + "," + time + "," + count + "\n")

                # print("info day", info_day)
                # print("data for the day", data_tmp)
                # print("some analysis for the day", analysis)
            w.close()

def is_doc_file(filename):
    _, file_ext = os.path.splitext(filename)
    return file_ext == '.doc' and is_valid_file(filename)

def create_directory(path, name):
    dir = path + "/" + name
    if not os.path.isdir(dir):
        os.mkdir(dir)

def can_process_year(year):
    return year in PARSEABLE_YEARS

# for local testing only
if __name__ == '__main__':
    process_adt_data(2019)
    # process2013_adt_data()
    # process2017_adt_data()
    # process2019_adt_data()

    # get_geo_data2013()
    # get_geo_data2017()

    # process2017_doc_data()
    # process2019_doc_data()

    pass
