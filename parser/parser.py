import codecs
import csv
import os
import profile
import re
import sys
import time

from pymongo import Connection
from django.template.defaultfilters import slugify

PARSER_PATH = os.path.abspath(os.path.dirname(__file__))

raw = os.path.join(PARSER_PATH, 'raw/')

'''
{
    'building code'
    'building name'
    'district code'
    'district name'
    
    'year':
        'dataset':
            'record':
                'name':
                    'value': value
                    'explainer': text
            'record'
            'record'


}

Data changes I made:

STATE.csv:
- in full states data, renamed columns to match data definition above.
- added full address column by combining addr2, city1, zip1.
'''

def UnicodeDictReader(utf8_data, **kwargs):
    '''
    from http://stackoverflow.com/questions/5004687/python-csv-dictreader-with-utf-8-data
    '''
    csv_reader = csv.DictReader(utf8_data, **kwargs)
    for row in csv_reader:
        yield dict([(key, value.decode('latin1')) for key, value in row.iteritems()])
        
def school_collection():
    connection = Connection('localhost', 27017)
    db = connection.schools
    return db.schools   

def remove_all():
    collection = school_collection()
    print str(collection.count()) + " remaining"
    print "Removing all"
    collection.remove({})
    print "Done"
    print str(collection.count()) + " remaining"
   
def get_school(building_code):
    collection = school_collection()
    school = collection.find_one({"Building Code": building_code})
    
    if school != None and building_code != '00000':
        return school
    else:
        return None       
        
def get_district(district_code):
    collection = school_collection()
    district = collection.find_one({"Building Code": '00000', "District Code": district_code})
    if district != None:
        return district
    else:
        return None 
        
def get_state():
    collection = school_collection()
    state = collection.find_one({"Statewide Record": True})
    return state   
    
def save(entity):
    collection = school_collection()
    collection.save(entity)

def ensure_year(record, year):
    if year not in record:
        record[year] = {}
    return record    
    
def ensure_dataset(record, year, dataset):
    if year not in record:
        record[year] = {}
        
    if dataset not in record[year]:
        record[year][dataset] = {}
        
    return record
    
def parse_gradestr(string):
    '''
    Grade range is imported with the basic data as GRADESTR
    '''
    l = string.split(',')
    l = [elt.strip() for elt in l] # cut out whitespace
    numbers_as_strings = ['1', '2','3','4','5','6','7','8','9','10','11','12']
    results = []
    for elt in l:   
        if '-' in elt:
            # This is either a grade range (eg '9-12', 'K-5')
            # Or just a string ('KG-Part')
            grade_range = elt.split('-')
            
            first_is_int, second_is_int = False, False
            if grade_range[0] in numbers_as_strings:
                grade_range[0] = int(grade_range[0])
                first_is_int = True
            
            if grade_range[1] in numbers_as_strings:
                grade_range[1] = int(grade_range[1])
                second_is_int = True
                
            if first_is_int and second_is_int:
                [results.append('grade_'+str(num)) for num in range(grade_range[0], grade_range[1]+1)]
            elif second_is_int:
                second = grade_range[1]
                while second != 0:
                    results.append('grade_'+str(second))
                    second -= 1
                results.append('grade_'+grade_range[0])
            else:
                results.append('grade_'+grade_range[0])
            
                              
        else:  
            results.append(elt)
            
    return results
        
        
def load_basic_data():
    '''
    This takes the list of all state building codes and inserts them into the
    database. That data is used as the base for all other imports.
    The dataset used is the 
    '''
    print "Loading basic data"
    
    filename = 'STATE.csv'
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
    
    # Get a database connection
    connection = Connection('localhost', 27017)
    db = connection.schools
    collection = db.schools
    
    records_to_insert = []
    districts_saved = []
    for line in raw_data:
        if line['Type'] not in exclude:
            line['2009-10'] = {} # Set up empty year dictionary for future inserts.
            
            # The state data stores building name and district name in the same
            # column, so here we figure out which one we're dealing with.
            if line['Building Code'] == '00000':
                line['District Name'] = line['Building Name']
            else:
                # The state data does not include district name for schools,
                # so we have to go back and get that from the data that has
                # already been saved.
                try:
                    line['District Name'] = get_district(line['District Code'])['District Name']
                except:
                    print line['District Code']
                    print districts_saved
                    assert False
                
                
            line['slug'] = slugify(line['Building Name'])
            line['district-slug'] = slugify(line['District Name'])
            
            # Save the districts one-by-one so that we can refer to them 
            # when creating building records.
                
            if line['Building Code'] == '00000':                    
                districts_saved.append(line['District Code'])
                save(line) 
            else:
                # Building records can be batch inserted.
                records_to_insert.append(line)
            
    collection.insert(records_to_insert)
    collection.save({'Statewide Record': True, '2009-10': {}}) #save a  dummy for the whole state.
    collection.ensure_index('Building Code')
    collection.ensure_index('District Code')
    
    
def generate_grade_strings():
    connection = Connection('localhost', 27017)
    db = connection.schools
    collection = db.schools
    
    buildings = collection.find({'Building Code': {'$ne':'00000'}})
    
    for building in buildings:
        try:
            building['grades'] = parse_gradestr(building['GRADESTR'])
            save(building)
        except:
            pass # the statewide record will throw an exception, so we ignore it.
    
    
def school_safety():
    print "Loading school safety"
    filename = 'School Safety Data 2009-2010-Table 1.csv'
    year = '2009-10'
    dataset = 'School Safety'
    
    path = os.path.join(raw, filename)        
    f = open(path, "r")
    raw_data = csv.DictReader(f, delimiter=',')
    
    state = {}
    districts = {}
    
    records_to_insert = []
    for line in raw_data:
        line['District Name'] = line['District Name'].rstrip()
        line['District Code'] = line['District Code'].rstrip()
        line['District Type'] = line['District Type'].rstrip()  
        line['ISD_Name'] = line['ISD_Name'].rstrip()

        line['Building Code'] = line['Building Code'].rstrip()
        line['Building Name'] = line['Building Name'].rstrip()
        line['Building Type'] = line['Building Type'].rstrip()

        line['County_Name'] = line['County_Name'].rstrip()
        line['County_ID'] = line['County_ID'].rstrip()
        
        elt = None
        if '00000' not in line['Building Code']:
            elt = get_school(line['Building Code'])
        
        if '00000' in line['Building Code'] :
            elt = get_district(line['District Code'])
            
        full_record = {}
        for key, value in line.iteritems():
            try:
                full_record[key] = { 'value': int(value) }
            except:
                full_record[key] = { 'value': value.rstrip() }
                
        # TODO: calculate percentages    
        #for key, value in line.iteritems():
        #    if isinstance(full_record[key], int):
        #        full_record['school_pct'+key] = float(line[key]) / float()
        #        full_record['state_pct_'+key] = state[key]
        #        full_record['district_pct_'+key] = float(districts[line['District Code']][key]) / float(districts[line['District Code']][key]) 
        
        # If this is an actual school (not a district or the state),
        # append the district data to the school record.
        if line['Building Code'] != '00000':
            if line['District Code'] in districts:
                district = districts[line['District Code']]
                for key in full_record:
                    full_record[key]['district'] = 0
                    # full_record[key]['state'] = state[key]['value']
        
        if '00000' in line['Building Code']:
            # If this is a district, save the district data in a temporary
            # dictionary, keyed by district code for esasy retrieval.
            districts[line['District Code']] = full_record

        if elt != None:  
            elt = ensure_year(elt, '2009-10') 
            elt = ensure_dataset(elt, '2009-10', 'school_safety')
            elt['2009-10']['school_safety'] = full_record
            save(elt)
        else:
            print line['Building Code'] + ' ' + line['Building Name'] + ' not found.'
            
    print "Done."
    
    
def aggregate_school_safety():
    records = school_collection()
    districts = records.distinct('District Code')
    for code in districts:
        schools = records.find({'District Code': code})
        schools = list(schools)
        
        if len(schools) != 0 and code and 'school_safety' in schools[0]['2009-10']:
            base = schools[0]['2009-10']['school_safety']
            for school in schools:
                # print school['2009-10']
                
                if school['2009-10']['school_safety'] == {}:
                    break
                
                for key, values in school['2009-10']['school_safety'].iteritems():
                    if isinstance(values, dict) and isinstance(values['value'], int):
                        try:
                            base[key]['district'] += values['value']
                        except:
                            pass
                
            for school in schools:
                if school['2009-10']['school_safety'] == {}:
                    break
                
                for key, values in school['2009-10']['school_safety'].iteritems():
                    if isinstance(values, dict) and isinstance(values['value'], int):
                        try:
                            school['2009-10']['school_safety'][key]['district'] = base[key]['district']
                        except:
                            pass
                
            for school in schools:
                save(school)
        
    
def meap():
    
    files = [
        ('meap/3rd_Grade_Public.csv', '3rd Grade'),
        ('meap/4th_Grade_Public.csv', '4th Grade'),
        ('meap/5th_Grade_Public.csv', '5th Grade'),
        ('meap/6th_Grade_Public.csv', '6th Grade'),
        ('meap/7th_Grade_Public.csv', '7th Grade'),
        ('meap/8th_Grade_Public.csv', '8th Grade'),
        ('meap/9th_Grade_Public.csv', '9th Grade')
    ]
    state = ''
    for file in files:
        print "Starting " + file[1]
        filename = file[0]
        grade = file[1]
        year = '2009-10'
        dataset = 'MEAP'
        
        state_exceeded = ''
        district_exceeded = {'00000':'N/A'}
    
        path = os.path.join(raw, filename)        
        f = open(path, "r")
        raw_data = csv.DictReader(f, delimiter=',')
        for line in raw_data:
            columns_to_float = [ 
            'AvgSS',
            'StdDev',
            'Level 1',	
            'Level 2',	
            'Level 3',	
            'Level 4',	
            'Met/Exceeded Standards',	
            'Did Not Meet Standards'
            ]
            for header in columns_to_float:
                try:
                    line[header] = float(line[header])
                except:
                    line[header] = None
                
            try:
                line['Number Tested'] = int(line['Number Tested'])
            except:
                line['Number Tested'] = None
        
            try:
                line['Number Included'] = int(line['Number Included'])
            except:
                line['Number Included'] = None
        

            entity = ''
            if '00000' not in line['Building Code']:   
                entity = get_school(line['Building Code'])
            elif '00000' not in line['District_Number']:
                entity = get_district(line['District_Number'])
                district_exceeded[line['District_Number']] = line['Met/Exceeded_Standards']
            else:
                entity = get_state()
                state_exceeded = line['Met/Exceeded_Standards']
                        
            if entity != None:
                # Checks if there already is 2009-10 MEAP data recorded
                # for this entity
                if 'MEAP' not in entity['2009-10']:
                    entity['2009-10']['MEAP'] = {}
            
                # Checks if there already is 2009-10 MEAP data for this grade
                # recorded for this entity
                if grade not in entity['2009-10']['MEAP']:
                    entity['2009-10']['MEAP'][grade] = {}
            
                # Records the MEAP subject
                subject = line['Subject']
                
                entity['2009-10']['MEAP'][grade][subject] = {
                    'value': line['Met/Exceeded_Standards'],
                    'district': district_exceeded[line['District_Number']],
                    'state':state_exceeded
                }
            
                save(entity)
                
                
def meap_district():
    files = [
        ('meap 2009 3-9 demographics/3rd.csv', '3rd Grade'),
       # ('meap 2009 3-9 demographics/4th.csv', '4th Grade'),
       # ('meap 2009 3-9 demographics/5th.csv', '5th Grade'),
       # ('meap 2009 3-9 demographics/6th.csv', '6th Grade'),
       # ('meap 2009 3-9 demographics/7th.csv', '7th Grade'),
       # ('meap 2009 3-9 demographics/8th.csv', '8th Grade'),
       # ('meap 2009 3-9 demographics/9th.csv', '9th Grade')
    ]
    state = ''
    for file in files:
        print "Starting " + file[1]
        filename = file[0]
        grade = file[1]
        year = '2009-10'
        dataset = 'MEAP'

        state_exceeded = ''
        district_exceeded = {'00000':'N/A'}

        path = os.path.join(raw, filename)        
        f = open(path, "r")
        raw_data = csv.DictReader(f, delimiter=',')
        for line in raw_data:
            #print line
            columns_to_float = [ 
            'AvgSS',
            'StdDev',
            'Level_1',	
            'Level_2',	
            'Level_3',	
            'Level_4',	
            'Met/Exceeded_Standards',	
            'Did Not Meet_Standards'
            ]
            for header in columns_to_float:
                try:
                    line[header] = float(line[header])
                except:
                    line[header] = None

            try:
                line['Number_Tested'] = int(line['Number_Tested'])
            except:
                line['Number_Tested'] = None

            try:
                line['Number_Included'] = int(line['Number_Included'])
            except:
                line['Number_Included'] = None


            entity = ''
            if '00000' not in line['District_Number']:
                entity = get_district(line['District_Number'])
                district_exceeded[line['District_Number']] = line['Met/Exceeded_Standards']
            else:
                entity = get_state()
                state_exceeded = line['Met/Exceeded_Standards']

            if entity != None:
                
                entity = ensure_dataset(entity, '2009-10','MEAP')

                # Checks if there already is 2009-10 MEAP data for this grade
                # recorded for this entity
                if grade not in entity['2009-10']['MEAP']:
                    entity['2009-10']['MEAP'][grade] = {}
                    
                # Records the MEAP subject
                subject = line['Subject']
                subgroup = slugify(line['Demographic_SubGroup']).replace("-","_")
                
                if subject not in entity['2009-10']['MEAP'][grade]:
                    entity['2009-10']['MEAP'][grade][subject] = {}
                    
                entity['2009-10']['MEAP'][grade][subject][subgroup] = {
                    'value': line['Met/Exceeded_Standards'],
                    'district': district_exceeded[line['District_Number']],
                    'state':state_exceeded,
                    'subgroup':line['Demographic_SubGroup']
                }

                save(entity)

            
def headcount_bldg_k12():
    dataset = 'headcount'
    
    filename = 'demographics/fall_2009_headcount_bldg_total_enroll_317470_7.csv'
    path = os.path.join(raw, filename)        
    
    district_file = 'demographics/fall_2009_headcount_dist_total_enroll_317526_7.csv'
    district_file = os.path.join(raw, district_file)
    
    state_file = 'demographics/fall_2009_headcount_state_total_enroll_317565_7.csv'
    state_file = os.path.join(raw, state_file)
    
    # Parse State results first. Used by school and district results
    state_file = open(state_file, "r")
    state_data = csv.DictReader(state_file, delimiter=',')
    state = {}
    for line in state_data:
        state = line
        
    # Then parse district results. Used by school results
    districts = {}
    district_file = open(district_file, "r")
    district_data = csv.DictReader(district_file, delimiter=',')
    for line in district_data:
        line['tot_all'] = int(line['tot_all'])
        districts[str(line['District Code'])] = line
        district = get_district(line['District Code'])
        if district != None:
            total_enrollment = int(line['tot_all'])
            for key, value in line.iteritems():
                try:
                    # Here, we convert all the number values from strings to ints.
                    # try-catch is used to avoid manually listing each field.
                    line[key] = {
                        'value': int(value),
                        'percent': int( float(value) / float(total_enrollment) * 100),
                        'state': int(float(state[key]) / float(state['tot_all']) * 100)
                    }
                except:
                    pass
            
            district = ensure_dataset(district, '2009-10', dataset)
            district['2009-10'][dataset] = line
            save(district)    

    # Open the schools file
    f = open(path, "r")
    raw_data = csv.DictReader(f, delimiter=',')
    
    print districts
    # Finally, parse school results
    for line in raw_data:
        entity = get_school(line['Building Code'])
        
        # If the school is already in the database:
        if entity != None:
            entity = ensure_year(entity, '2009-10')
            
            total_enrollment = int(line['tot_all'])
            
            for key, value in line.iteritems():
                try:
                    line[key] = {
                        'value': int(value),
                        'percent': int( float(value) / float(total_enrollment) * 100),
                        'district': int(float(districts[line['District Code']][key]['value']) / float(districts[line['District Code']]['tot_all']['value']) * 100),
                        'state': int(float(state[key]) / float(state['tot_all']) * 100)
                    }
                except:
                    print key, value
                    
            entity['2009-10'][dataset] = line
            save(entity)
            
        else:
            print line['Building Name'] + " not found."
    
    
def ACT_breakdowns():
    print "Starting 2010 ACT breakdowns"
    filename = 'ACT_School_and_District_Data_File_-_Spring_2010_MME_328541_7.csv'
    path = os.path.join(raw, filename)        
    f = open(path, "r")
    raw_data = csv.DictReader(f, delimiter=',')
    
    districts = {}
    state = {}
    
    for line in raw_data:
        entity = None
        if '00000' not in line['Building Code']:   
            entity = get_school(line['Building Code'])
        elif '00000' not in line['District Code']:
            entity = get_district(line['District Code'])
        else:
            entity = get_state()

        if entity is not None:
            entity = ensure_year(entity, '2010')
            entity = ensure_dataset(entity, '2010', 'ACT')
            
            try:
                line["Number Tested"] = int(line["Number Tested"])
            except:
                pass
                
            try:
                line["Mean"] = float(line["Mean"])
            except:
                pass
                
            try:
                line['Stdev'] = float(line['Stdev'])
            except:
                pass
                
            subject = line['Subject']
            entity['2010']['ACT'][subject] = line
            
            if '00000' in line['Building Code'] and '00000' in line['District Code']:
                state[line['Subject']] = line
            elif '00000' in line['Building Code'] and '00000' not in line['District Code']:
                if line['District Code'] not in districts:
                    districts[line['District Code']] = {}
                districts[line['District Code']][line['Subject']] = line
                
            else:
                try:
                    line['state'] = state[line['Subject']]['Mean']
                    line['district'] = districts[line['District Code']][line['Subject']]['Mean']
                except:
                    print "No match for " + line['School Name']
            
            save(entity)
            
        
def reduced_free_lunch_schools():
    print "Starting 2009 Reduced/Free Lunch Eligible"
    filename = 'reduced_lunch/Fall_2009_FRL_Bldg_318585_7/Bldg_K-12-Table 1.csv'
    path = os.path.join(raw, filename)        
    f = open(path, "r")
    raw_data = csv.DictReader(f, delimiter=',')
    
    for line in raw_data:
        
        entity = get_school(line['Building Code'])
        if entity != None:
            try:
                line['free_lunch_eligible'] = int(line['free_lunch_eligible'])
                line['free_lunch_eligible_pct'] = int(float(line['free_lunch_eligible']) / float(line['Total Count']) * 100)
            except:
                pass
        
            try:
                line['reduced_price_lunch_eligible'] = int(line['reduced_price_lunch_eligible'])
                line['reduced_price_lunch_eligible_pct'] = int(float(line['reduced_price_lunch_eligible'] / float(line['Total Count']) ) * 100)
            except:
                pass
            
            entity = ensure_dataset(entity, '2009-10', 'reduced_lunch')
            entity['2009-10']['reduced_lunch'] = line
            save(entity)
        
        
def reduced_free_lunch_districts():
    print "Starting 2009 Reduced/Free Lunch Eligible by District"
    filename = 'reduced_lunch/Fall_2009_FRL_District_318584_7/Dist_K-12-Table 1.csv'
    path = os.path.join(raw, filename)        
    f = open(path, "r")
    raw_data = csv.DictReader(f, delimiter=',')

    for line in raw_data:

        entity = get_district(line['District Code'])
        if entity != None:
            print "ok!"
            
            try:
                line['free_lunch_eligible'] = int(line['free_lunch_eligible'])
                line['free_lunch_eligible_pct'] = int(float(line['free_lunch_eligible']) / float(line['Total Count']) * 100)
            except:
                print "hey!"
                pass

            try:
                line['reduced_price_lunch_eligible'] = int(line['reduced_price_lunch_eligible'])
                line['reduced_price_lunch_eligible_pct'] = int(float(line['reduced_price_lunch_eligible'] / float(line['Total Count']) ) * 100)
            except:
                print "hey!"
                
                pass

            entity = ensure_dataset(entity, '2009-10', 'reduced_lunch')
            entity['2009-10']['reduced_lunch'] = line
            save(entity)

    
def bulletin_1014():
    # From Bulletin 1014- Michigan Public Schools Ranked by Select Financial Information
    print "Starting Bulletin 1014"
    filename = 'financials/2009_1014_bulletin.csv'
    path = os.path.join(raw, filename)        
    f = open(path, "r")
    raw_data = csv.DictReader(f, delimiter=',')
    
    for line in raw_data:
        
        entity = get_district(line['DCODE'])
        if entity != None:
            entity = ensure_dataset(entity, '2009-10', 'ten_fourteen')
            
            for key, value in line.iteritems():
                try:
                    if '.' in value:
                        line[key] = float(value)
                    else:
                        line[key] = int(value)
                        
                except:
                    pass
            
            entity['2009-10']['ten_fourteen'] = line
            save(entity)
    
    
def bulletin_1011():
    # From Bulletin 1014- Michigan Public Schools Ranked by Select Financial Information
    print "Starting Bulletin 1011"
    filename = 'financials/2008-9_1011_bulletin.csv'
    path = os.path.join(raw, filename)        
    f = open(path, "r")
    raw_data = csv.DictReader(f, delimiter=',')

    districts = {}
    for line in raw_data:
        
        # save these before we convert them to int/float
        district = line['DCODE']
        field = line['FIELD']
        
        for key, value in line.iteritems():
            try:
                if '.' in value:
                    line[key] = float(value)
                else:
                    line[key] = int(value)

            except:
                pass
              
        if district in districts:
            districts[district][field] = line
        else:
            districts[district] = { field: line }
            
    for district, data in districts.iteritems():
        entity = get_district(district)
        
        if entity != None:
            entity = ensure_dataset(entity, '2008-9', 'ten_eleven')
            entity['2008-9']['ten_eleven'] = data
            save(entity)
    
    
def ayp_met():
    print "Starting 2010 schools that met AYP"
    filename = 'ayp/2010/Schools Met AYP-Table 1.csv'
    path = os.path.join(raw, filename)        
    f = open(path, "r")
    raw_data = csv.DictReader(f, delimiter=',')
    
    for line in raw_data:
        entity = get_school(line['Building Code'])
        if entity != None:
            
            entity = ensure_dataset(entity, '2009-10', 'ayp')
            entity['2009-10']['ayp'] = line
            entity['2009-10']['ayp']['passed'] = True
            
            save(entity)
            
def ayp_not_met():
    print "Starting 2010 schools that did not meet AYP"
    filename = 'ayp/2010/Schools Not Met AYP-Table 1.csv'
    path = os.path.join(raw, filename)        
    f = open(path, "r")
    raw_data = csv.DictReader(f, delimiter=',')

    for line in raw_data:
        entity = get_school(line['Building Code'])
        if entity != None:

            entity = ensure_dataset(entity, '2009-10', 'ayp')
            entity['2009-10']['ayp'] = line
            entity['2009-10']['ayp']['passed'] = False

            save(entity)

            
            
    
        
remove_all()
load_basic_data()
school_safety()
#aggregate_school_safety()
meap()
meap_district()
headcount_bldg_k12()
reduced_free_lunch_schools()
reduced_free_lunch_districts()
bulletin_1014()
bulletin_1011()
ACT_breakdowns()
generate_grade_strings()
ayp_met()
ayp_not_met()