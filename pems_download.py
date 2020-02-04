import os
import webbrowser
import time
import requests


DETECTOR_IDS = [403250]
# DETECTOR_IDS = [403250, 403256, 403255, 403257, 418387, 418388, 400376,
#                413981, 413980, 413982, 402794, 413983, 413984, 413985,
#                413987, 413986, 402796, 413988, 402799, 403251, 403710,
#                403254, 403719, 400566, 418420, 418419, 418422, 418423,
#                402793, 403226, 414015, 414016, 402795, 402797, 414011,
#                402798]

"""
Get url add-on for a given year
"""
def time_for_year(year):
    if year == 2013:
        url_addon = "&s_time_id=1362441600"
        url_addon = url_addon + "&s_time_id_f=" + "03" + "%2F" + "05" + "%2F" + "2013" + "+00%3A00"
        url_addon = url_addon + "&e_time_id=1362700740"
        url_addon = url_addon + "&e_time_id_f=" + "03" + "%2F" + "07" + "%2F" + "2013" + "+23%3A59"
    if year == 2017:
        url_addon = "&s_time_id=1488844800"
        url_addon = url_addon + "&s_time_id_f=" + "03" + "%2F" + "07" + "%2F" + "2017" + "+00%3A00"
        url_addon = url_addon + "&e_time_id=1489103940"
        url_addon = url_addon + "&e_time_id_f=" + "03" + "%2F" + "09" + "%2F" + "2017" + "+23%3A59"
    if year == 2019:
        url_addon = "&s_time_id=1551744000"
        url_addon = url_addon + "&s_time_id_f=" + "03" + "%2F" + "05" + "%2F" + "2019" + "+00%3A00"
        url_addon = url_addon + "&e_time_id=1552003140"
        url_addon = url_addon + "&e_time_id_f=" + "03" + "%2F" + "07" + "%2F" + "2019" + "+23%3A59"
    return url_addon


# &s_time_id=1362441600
# &s_time_id_f=03%2F05%2F2013+00%3A00
# &e_time_id=1362700740
# &e_time_id_f=03%2F07%2F2013+23%3A59


# &s_time_id=1488844800
# &s_time_id_f=03%2F07%2F2017+00%3A00
# &e_time_id=1489103940
# &e_time_id_f=03%2F09%2F2017+23%3A59


# s_time_id=1551744000
# &s_time_id_f=03%2F05%2F2019+00%3A00
# &e_time_id=1552003140
# &e_time_id_f=03%2F07%2F2019+23%3A59

"""
For a given year get the transportation data using station ids for that year
"""
def download(year, detector_ids):
    for i in detector_ids:
        url = 'http://pems.dot.ca.gov/?report_form=1'
        url = url + "&dnode=VDS"
        url = url + "&content=loops"

        url = url + "&tab=det_timeseries"
        url = url + "&export=xls"

        url = url + "&station_id=" + str(i)

        url = url + time_for_year(year)

        url = url + "&tod=all"
        url = url + "&tod_from=0"
        url = url + "&tod_to=0"
        url = url + "&dow_0=on"
        url = url + "&dow_1=on"
        url = url + "&dow_2=on"
        url = url + "&dow_3=on"
        url = url + "&dow_4=on"
        url = url + "&dow_5=on"
        url = url + "&dow_6=on"
        url = url + "&holidays=on"
        url = url + "&q=flow"
        url = url + "&q2="
        url = url + "&gn=5min"
        url = url + "&agg=on"
        url = url + "&lane1=on"
        url = url + "&lane2=on"
        url = url + "lane3=on"

        print(url)
        # webbrowser.open(url, new=2)
        # time.sleep(10)
        # os.rename(r'pems_output.xlsx', r'' + str(i) + "_" + str(year) + ".xlsx")

        file_name = str(i) + "_" + str(year) + ".xlsx"
        file_path = os.getcwd() + "/" + file_name
        data = {'username' : 'ed.romero@berkeley.edu', 'password' : 'W3+ulperk',
                'redirect' : "%2F%3Freport_form%3D1%26dnode%3DVDS%26content%3Dloops%26tab%3Ddet_timeseries%26export%3Dxls%26station_id%3D403250%26s_time_id%3D1488844800%26s_time_id_f%3D03%252F07%252F2017%2B00%253A00%26e_time_id%3D1489103940%26e_time_id_f%3D03%252F09%252F2017%2B23%253A59%26tod%3Dall%26tod_from%3D0%26tod_to%3D0%26dow_0%3Don%26dow_1%3Don%26dow_2%3Don%26dow_3%3Don%26dow_4%3Don%26dow_5%3Don%26dow_6%3Don%26holidays%3Don%26q%3Dflow%26q2%3D%26gn%3D5min%26agg%3Don%26lane1%3Don%26lane2%3Donlane3%3Don",
                'login' : 'Login'}
        r = requests.post('http://pems.dot.ca.gov/', data=data, headers = dict(referer=url))
        print('status', r.ok)
        r = requests.get(url, allow_redirects=True)
        with open(file_path, 'wb') as f:
            f.write(r.content)
            f.close()
            r.close()


# local testing
if __name__ == '__main__':
    download(2017, DETECTOR_IDS)
    pass
