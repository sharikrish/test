import urllib.request, urllib.parse
import argparse
import json
import os, ssl
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict

def getSequenceSummary(sequence_url, header_dict, query_dict={}):
    # Build the required JSON data for the post request. The user
    # of the function provides both the header and the query data
    url_dict = dict()
    #url_dict.update(header_dict)
    url_dict.update(query_dict)
    url_data = urllib.parse.urlencode(url_dict).encode()

    # Try to make the connection and get a response.
    try:
        request = urllib.request.Request(sequence_url, url_data, header_dict)
        #response = urllib.request.urlopen(sequence_url, data=url_data)
        response = urllib.request.urlopen(request)
        url_response = response.read().decode(response.headers.get_content_charset())
    except urllib.error.HTTPError as e:
        print('Error: Server could not fullfil the request')
        print('Error: Error code =', e.code)
        print(e.read())
        return json.loads('[]')
    except urllib.error.URLError as e:
        print('Error: Failed to reach the server')
        print('Error: Reason =', e.reason)
        return json.loads('[]')
    
    # Convert the response to JSON so we can process it easily.
    json_data = json.loads(url_response)
    
    # Print out the summary stats for the repository.
    sample_summary = json_data['summary']

    # Return the JSON of the results.
    return sample_summary

def getSamples(sample_url, header_dict, query_dict={}):
    # Build the required JSON data for the post request. The user
    # of the function provides both the header and the query data
    url_dict = dict()
    #url_dict.update(header_dict)
    url_dict.update(query_dict)
    url_data = urllib.parse.urlencode(url_dict).encode()

    # Try to connect the URL and get a response. On error return an
    # empty JSON array.
    try:
        request = urllib.request.Request(sample_url, url_data, header_dict)
        #response = urllib.request.urlopen(sample_url, data=url_data, headers=header_dict)
        response = urllib.request.urlopen(request)
        url_response = response.read().decode(response.headers.get_content_charset())
    except urllib.error.HTTPError as e:
        print('Error: Server could not fullfil the request')
        print('Error: Error code =', e.code)
        print(e.read())
        return json.loads('[]')
    except urllib.error.URLError as e:
        print('Error: Failed to reach the server')
        print('Error: Reason =', e.reason)
        return json.loads('[]')

    # Convert the response to JSON so we can process it easily.
    # print(url_response)
    json_data = json.loads(url_response)
    # Return the JSON data
    return json_data

def getHeaderDict():
    # Set up the header for the post request.
    header_dict = {'accept': 'application/json',
                   'Content-Type': 'application/x-www-form-urlencoded'}
    return header_dict

def initHTTP():
    # Deafult OS do not have create cient certificate bundles. It is
    # easiest for us to ignore HTTPS certificate errors in this case.
    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
        getattr(ssl, '_create_unverified_context', None)): 
        ssl._create_default_https_context = ssl._create_unverified_context

def performQueryAnalysis(base_url, query_key, query_values):
    # Ensure our HTTP set up has been done.
    initHTTP()
    # Get the HTTP header information (in the form of a dictionary)
    header_dict = getHeaderDict()

    # Select the API entry points to use, based on the base URL provided
    sample_url = base_url+'/v2/samples'
    sequence_url = base_url+'/v2/sequences_summary'

    # Get the sample metadata for the query. We want to keep track of each sample
    sample_json = getSamples(sample_url, header_dict)
    # Create a dictionary with keys as the ID for the sample.
    sample_dict = dict()
    # For each sample, create an empty dictionary (to be filled in later)
    for sample in sample_json:
        sample_dict[str(sample['_id'])] = dict()

    # Iterate over the query values of interest. One query per value gives us results
    # for all samples so this is about as efficient as it gets.
    for value in query_values:
        # Create and do the query for this value.
        query_dict = dict()
        query_dict.update({query_key: value})
        print('Performing query: ' + str(query_key) + ' = ' + str(value))
        sequence_summary_json = getSequenceSummary(sequence_url, header_dict, query_dict)
        #print(sequence_summary_json)
        # The query gives us a count for each sample. We iterate over the samples to do some
        # bookkeeping for that sample.
        for sample in sequence_summary_json:
            # Get the dictionaries of values for this sample
            #print(sample['sample_id'])
            value_dict = sample_dict[str(sample['_id'])]
            # Update the count for the value we are considering
            filtered_sequence_count = sample['ir_filtered_sequence_count']
            value_dict.update({value:filtered_sequence_count})
            sample_dict[str(sample['_id'])] = value_dict
            print('   ' + query_key + ' ' + str(value) + ' = ' + str(sample['ir_filtered_sequence_count']))

    # Create the data structure required for the graphing...
    data = dict()
    grand_total = 0
    graph_total = 0
    # Iterate over the samples.
    for sample in sample_json:
        # Print out some summary information for this sample.
        value_dict = sample_dict[str(sample['_id'])] 
        sequence_count = sample['ir_sequence_count']
        grand_total = grand_total + sequence_count
        print('\nsample = ' + sample['sample_id'] + ' (' + str(sequence_count) + ')')
        total = 0
        # Iterate over the values that we have accumulated.
        for key, value in value_dict.items():
            # Add up the total count for each key and store it.
            if key in data:
                data.update({key:data[key]+value})
            else:
                data.update({key:value})
            print(str(key) + ' = ' + str(value) + ' (' + '%.2f' % ((value/sequence_count)*100.0) + '%)')
            total = total + value
            graph_total = graph_total + value
        # More summary information for this sample
        if sequence_count > 0:
            percent = (total/sequence_count)*100
        else:
            percent = 0
        print('sample = ' + sample['sample_id'] + ' (' + str(total) + ' %.2f'%(percent) + '%)')
        
    # Finally, dump out the actual data we are going to graph...
    print('\nGraph data overview - ' + query_key + ':')
    for key, value in data.items():
        print(str(key) + ' = ' + str(value))
    if grand_total > 0:
        percent = (graph_total/grand_total)*100
    else:
        percent = 0
    print('graph total = ' + str(graph_total) + ' %.2f'%(percent) + '%')

    # Return the data.
    return data

def plotData(plot_names, plot_data, title, filename):
    # Set up the plot
    
    plt.rcParams.update({'figure.autolayout': True})
    fig, ax = plt.subplots()
     # Remove warning
    fig.set_tight_layout(False)
    # Make it a bar graph using the names and the data provided
    ax.barh(plot_names, plot_data)
    # Write the graph to the filename provided.
    fig.savefig(filename, transparent=False, dpi=80, bbox_inches="tight")
    print('Saved image in ' + filename)


def getArguments():
    # Set up the command line parser
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=""
    )

    # Field in the API to use for the histogram
    parser.add_argument("api_field")
    # Values to search for in the field to generate the histogram
    parser.add_argument("graph_values")
    # The URL for the repository to search
    parser.add_argument("base_url")
    # Verbosity flag
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Run the program in verbose mode.")

    # Parse the command line arguements.
    options = parser.parse_args()
    return options


if __name__ == "__main__":
    # Get the command line arguments.
    options = getArguments()
    # Split the comma separated input string.
    values = options.graph_values.split(',')
    # Perform the query analysis, gives us back a dictionary.
    data = performQueryAnalysis(options.base_url, options.api_field, values)
    sorted_data = OrderedDict(sorted(data.items(), key=lambda t: t[0]))
    # Graph the results
    title = options.api_field
    filename = options.api_field + ".png"
    plotData(list(sorted_data.keys()), list(sorted_data.values()), title, filename)

    # Return success
    sys.exit(0)

