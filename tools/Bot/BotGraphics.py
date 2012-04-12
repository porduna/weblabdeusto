#!/usr/bin/env python
#-*-*- encoding: utf-8 -*-*-
#
# Copyright (C) 2005-2009 University of Deusto
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# This software consists of contributions made by many individuals, 
# listed below:
#
# Author: Pablo Orduña <pablo@ordunya.com>
#

import os
import json

from BotMisc import show_time, flush
import Configuration
import platform

import matplotlib
matplotlib.use(Configuration.MATPLOTLIB_BACKEND)
import matplotlib.pyplot as plt

METHODS = ["login", "list_experiments", "reserve_experiment", "get_reservation_status", "logout", "finished_experiment", "send_file", "send_command", "poll", "get_user_information"]
CALL_TIMES = ('avg_call_times', 'min_call_times', 'max_call_times')

GET_FIGURE_FILENAME_CODE="""def get_figure_filename(protocol, method, date):
    return "figures" + os.sep + "figure_" + date + "_" + protocol + "_" + method + ".png"
"""

exec(GET_FIGURE_FILENAME_CODE)

def generate_html(protocols, methods, date):

    # Retrieve this information in Linux systems
    try:
        model_name = [ line for line in open("/proc/cpuinfo").readlines() if line.startswith("model name") ][0]
        model_name = ':'.join(model_name.split(': ')[1:]).strip()
        while '  ' in model_name:
            model_name = model_name.replace('  ',' ')

        ram = [ line.split(' ')[-2] for line in open("/proc/meminfo").readlines() if line.startswith("MemTotal:")][0]
        memory = '%.2fGB' % ( int(ram) / (1024.0 * 1024.0))
    except:
        system_info = Configuration.SYSTEM
    else:
        system_info = "%s %s" % (model_name, memory)

    all_system_info = "%s; %s; Python %s" % (system_info, platform.platform(), platform.python_version())

    page = """<html><head><title>Bot stats as of %s</title></head><body>
    <h1>Bot stats as of %s</h1>
    <h2>Stats information</h2>
    Configuration: %s<br/>
    System: %s<br/>
    <a name="index"><h2>Index</h2></a>
    <ul>
    """ % (date, date,Configuration.RUNNING_CONFIGURATION, all_system_info)

    for protocol in protocols:
        page += """\t<li><a href="#%s">%s</a>: <ul>""" % (protocol, protocol)
        for method in methods:
            page += """\t\t<li><a href="#%s_%s">%s</a></li>\n""" % (protocol, method, method)
        page += """\t</ul></li>\n"""

    page += """</ul><h2>Results</h2>\n"""
    for protocol in protocols:
        page += """<br/><br/><a name="%s"><h3>%s</h3></a><center>\n""" % (protocol, protocol)

        for method in methods:
            page += """<a name="%s_%s"><h4>%s</h4></a>\n""" % (protocol, method, method)
            figure_filename = get_figure_filename(protocol, method, date)
            page += """<a href="%s"><img width="500" src="%s"/></a>\n""" % (figure_filename, figure_filename)
            page += """<br/>\n"""
            page += """<a href="#index">Back to index</a>"""
        page += """</center>"""

    page += """</body></html>"""
    return page

def print_results(raw_information, date, verbose = True):
    working_methods = METHODS[:]

    all_data = {
        # method : {
        #      protocol : {
        #          max:  (x,y),
        #          min:  (x,y),
        #          mean: (x,y)
        #      },
        # }
    }

    LINES = ('std','max','min','avg')

    protocols = set()

    for method in METHODS:
        method_data = {}
        all_data[method] = method_data

        for line in LINES:
            def func_on_results(results):
                return getattr(results, line + '_call_times')[method]

            data = {}
            data['protocols'] = raw_information.keys()
            for protocol in data['protocols']:
                try:
                    x, y = raw_information[protocol]
                    y = map(func_on_results, y)
                except KeyError, ke:
                    continue
                except: 
                    import traceback
                    traceback.print_exc()
                    continue
                else:
                    protocols.add(protocol)
                    if not protocol in method_data:
                        method_data[protocol] = {}
                    protocol_data = method_data[protocol]
                    protocol_data[line] = x,y

    for method in METHODS:
        if len(all_data[method]) == 0:
            working_methods.remove(method)
    
    # START PRINTING THIS PART

    CODE="""#!/usr/bin/env python
import os
import matplotlib.pyplot as plt

%(get_figure_filename)s

def print_figures():
    
    date            = %(date)r
    working_methods = %(working_methods)r
    all_data        = %(all_data)s

    for method in working_methods:
        method_data = all_data[method]
        for protocol in method_data:
            protocol_data = method_data[protocol]
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.set_xlabel("Users")
            ax.set_ylabel("Time (sec)")

            x, y = protocol_data['max']
            ax.plot(x, y, 'r-')
            x, y = protocol_data['avg']
            _, yerr = protocol_data['std']
            ax.errorbar(x, y, yerr=yerr, fmt='g-')
            x, y = protocol_data['min']
            ax.plot(x, y, 'b-')

            plt.savefig(get_figure_filename(protocol, method, date))

if __name__ == '__main__':
    print_figures()
    """ % {
        'get_figure_filename' : GET_FIGURE_FILENAME_CODE,
        'working_methods'     : working_methods,
        'all_data'            : json.dumps(all_data, indent=4),
        'date'                : date
    }

    generate_figures_script = "figures%sgenerate_figures_%s.py" % (os.sep, date)
    open(generate_figures_script,'w').write(CODE)

    execfile(generate_figures_script)

    html = generate_html(protocols, working_methods, date)
    html_filename = 'botclient_%s.html' % date
    open(html_filename, 'w').write(html)

    # END PRINTING THIS PART

    if verbose:
        print "HTML file available in",html_filename
        print "Finished plotting; %s" % show_time()
        flush()

if __name__ == '__main__':
    DATE = "D_2012_04_12_T_09_53_03"

    from BotInformationRetriever import get_raw_information
    raw_information = get_raw_information(DATE)
    print_results(raw_information, DATE)

