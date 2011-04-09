import codecs
from copy import deepcopy
import csv
import imp
import os
import profile
import re
import sys
import time

from core.models import School
from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import slugify

PARSER_PATH = os.path.abspath(os.path.dirname(__file__))

def UnicodeDictReader(utf8_data, **kwargs):
    '''
    from http://stackoverflow.com/questions/5004687/python-csv-dictreader-with-utf-8-data
    '''
    csv_reader = csv.DictReader(utf8_data, **kwargs)
    for row in csv_reader:
        yield dict([(key, value.decode('latin1')) for key, value in row.iteritems()])

class Command(BaseCommand):
        
    def handle(self, *args, **options):
    
        School.objects.all().delete()
    
        print "Loading basic data"
    
        filename = 'STATE.csv'
        raw = os.path.join(PARSER_PATH, 'raw/')
        path = os.path.join(raw, filename)        
        f = open(path, "r")
        raw_data = UnicodeDictReader(f, delimiter=',')
    
        '''
        We don't import some school codes because they are not immediately relevant
        for the application. Here is the reference list as far as I can suss it out.
        Will need to find the actual reference list.
        1: No idea
        2: ISDs
        3: districts
        4: charter?
        5: Also ISDs?
        6: religious
        7: service buildings, planetariums, etc.
        8: corrections
        9: special academies  (charter?)
        10: state
        '''
        exclude = ['01', '06', '07'] 
    
        records_to_insert = []
        districts_saved = {}
        for line in raw_data:
            if line['Type'] not in exclude:
            
                entry = School()
                # The state data stores building name and district name in the same
                # column, so here we figure out which one we're dealing with.
            
                if line['Building Code'] == '00000':
                    line['District Name'] = line['Building Name']
                    entry.district_name =  line['Building Name']
                    entry.district_code = line['District Code']
                    entry.building_code = '00000'
                else:
                    entry.building_name = line['Building Name']
                    entry.building_code = line['Building Code']
                    # The state data does not include district name for schools,
                    # so we have to go back and get that from the data that has
                    # already been saved.
                    try:
                        entry.district_name = districts_saved[line['District Code']]['District Name']
                    except:
                        print line['District Code']
                        print districts_saved
                        assert False
                
                
                entry.slug = slugify(line['Building Name'])
                entry.district_slug = slugify(entry.district_name)
            
                # Save the districts one-by-one so that we can refer to them 
                # when creating building records.
                if line['Building Code'] == '00000':                    
                    districts_saved[line['District Code']] = line
            
                entry.save()
                
