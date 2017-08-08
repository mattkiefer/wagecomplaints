import csv
from complaints.models import MWOT, WC, Hearing
from wagecomplaints.settings import BASE_DIR
from census.models import Zip
from pprint import pprint

reports_dir = BASE_DIR + '/reports/'

mwots = [x for x in MWOT.objects.all()]
wcs = [x for x in WC.objects.all()]

cases = mwots + wcs

hearings = [x for x in Hearing.objects.all()]
wcs_with_hearings = [x.case for x in hearings if x.case]

zips = [x for x in Zip.objects.all()]
chicago_zip_codes = [x['ZIP'] for x in csv.DictReader(open(reports_dir + 'Zip_Codes.csv'))]

def avg_case_time(cases):
    """
    given a list of cases,
    returns the average number of days
    from filed to close
    where both values exist
    """
    date_diffs = [(x.date_closed - x.date_filed).days for x in cases if x.date_closed and x.date_filed]
    return round(sum(date_diffs)/float(len(date_diffs)))


def status_counts(cases):
    """
    given a list of cases,
    returns breakdown of case statuses,
    including counts and pct of total
    """
    status_counts = {}
    for x in cases:
        if x.status not in status_counts:
            status_counts[x.status] = {}
            status_counts[x.status]['count'] = 0
        status_counts[x.status]['count'] += 1
    total = len(cases)
    for status in status_counts:
        status_counts[status]['pct'] = round(status_counts[status]['count']*100/float(total))
    status_counts['total'] = {}
    status_counts['total']['count'] = total
    status_counts['total']['pct'] = 100
    return status_counts


def industry_counts(cases):
    """
    given a list of cases,
    returns breakdown of industries,
    including counts, pct of total, paid/dismissed rates
    writes results to file
    """
    industry_counts = {}
    for x in cases:
        if x.industry not in industry_counts:
            industry_counts[x.industry] = {}
            industry_counts[x.industry]['cases'] = []
        industry_counts[x.industry]['cases'].append(x)
    total = len(cases)
    for industry in industry_counts:
        industry_counts[industry]['count'] = len(industry_counts[industry]['cases'])
        industry_counts[industry]['pct_of_total'] = round(industry_counts[industry]['count']/float(total)*100,2)
        industry_counts[industry]['paid_count'] = len([x for x in industry_counts[industry]['cases'] if x.status == 'Paid'])
        industry_counts[industry]['dismissed_count'] = len([x for x in industry_counts[industry]['cases'] if x.status == 'Dismissed'])
    industry_counts['total'] = {}
    industry_counts['total']['count'] = total
    industry_counts['total']['pct_of_total'] = 100
    industry_counts['total']['paid_count'] =  len([x for x in cases if x.status == 'Paid']) 
    industry_counts['total']['dismissed_count'] = len([x for x in cases if x.status == 'Dismissed'])

    # outfile setup
    file_name = 'industries.csv'
    outfile = open(reports_dir + file_name,'w')
    outcsv = csv.DictWriter(outfile,['industry','count','pct_of_total','paid_count','dismissed_count'])
    outcsv.writeheader()

    rows = []
    for industry in industry_counts:
        try:
            row = {'industry': industry, 'count': industry_counts[industry]['count'], 'pct_of_total': industry_counts[industry]['pct_of_total'],
                'paid_count':industry_counts[industry]['paid_count'], 'dismissed_count': industry_counts[industry]['dismissed_count']}
            outcsv.writerow(row)
            rows.append(row)
        except Exception, e:
            print e
            import ipdb; ipdb.set_trace()
    outfile.close()
    return(rows)

def top_zip_codes(limit=100):
    # outfile setup
    file_name = 'zips.csv'
    outfile = open(reports_dir + file_name,'w')
    outcsv = csv.DictWriter(outfile,['zip_code', 'pct_hisp', 'pct_blk', 'pct_white', 'pct_frn_born', 'pct_poverty', 'case_count'])
    outcsv.writeheader()

    # get data
    ordered_zips = sorted([x for x in Zip.objects.all()], key = lambda x: len(x.complaint_set.all()), reverse = True)
    for x in ordered_zips[0:limit]:
        outcsv.writerow(
                        {
                         'zip_code':x.zip_code,
                         'pct_hisp':x.pct_hisp,
                         'pct_blk':x.pct_blk,
                         'pct_white':x.pct_white,
                         'pct_frn_born':x.pct_frn_born,
                         'pct_poverty':x.pct_poverty,
                         'case_count': len(x.complaint_set.all()),
                        }
                       )
    outfile.close()


def breakdown(case_list,interval,crosstabs=[],outfile='buffer.csv'):
    """
    return cases by
    time interval to resolve,
    optional crosstabs
    """
    closed_cases = [x for x in case_list if x.date_closed and x.date_filed \
            and x.date_closed > x.date_filed]
    interval_breakdown = dict()
    total = 0
    for case in closed_cases:
        try:
            lifespan = (case.date_closed - case.date_filed).days
            multiplier = lifespan / interval 
            lower_range = (interval * multiplier) + 1
            upper_range = interval * (multiplier + 1)
            bucket = upper_range
            if bucket not in interval_breakdown:
                interval_breakdown[bucket] = []
                # TODO breakdown crosstabs here
            interval_breakdown[bucket].append(case)
            total += 1
        except Exception, e:
            print e
            import ipdb; ipdb.set_trace()
    print 'breakdown'
    for key in sorted(interval_breakdown.keys()):
        print key, ':', str(len(interval_breakdown[key]))
    return interval_breakdown


def early_dismissal_time_series(cutoff_days=61):
    print ','.join(['month,year','pct_closed_within_' + str(cutoff_days) + '_days','pct_dismissed','pct_paid'])
    month_years = sorted(set([(wc.date_filed.month, wc.date_filed.year) \
            for wc in wcs if wc.date_filed]), key = lambda x: (x[1],x[0]))
    for month_year in month_years:
        month = month_year[0]
        year = month_year[1]
        filed_this_mo = WC.objects.filter(date_filed__month=month,date_filed__year=year)
        closed_by_cutoff = [x for x in filed_this_mo if x.date_closed and \
                (x.date_closed - x.date_filed).days <= cutoff_days]
        closed_dismissed = [x for x in closed_by_cutoff if x.status == 'Dismissed']
        closed_paid = [x for x in closed_by_cutoff if x.status == 'Paid']
        print (month_year, 
              round(len(closed_by_cutoff)/float(len(filed_this_mo)),2),
              round(len(closed_dismissed)/float(len(filed_this_mo)),2),
              round(len(closed_paid)/float(len(filed_this_mo)),2),
              )
   
        
def complaints_by_wkf_and_race(min_wkf=2500):
    outfile_name = 'zip_wfk_race.csv'
    outfile = open(reports_dir + outfile_name,'w')
    outcsv = csv.DictWriter(outfile,['zip','comp_pct_wkf','hisp','blk','non-w'])
    outcsv.writeheader()
    data = []
    for z in zips:
        if z.cnt_workforce > min_wkf:
            data.append({
                         'zip'            : z.zip_code,
                         'comp_pct_wkf'   : round(float(len(z.complaint_set.all()))/z.cnt_workforce*100,2),
                         'hisp'           : round(z.pct_hisp / float(sum([z.pct_blk, z.pct_hisp, z.pct_white]))*100,2),
                         'blk'            : round(z.pct_blk / float(sum([z.pct_blk, z.pct_hisp, z.pct_white]))*100,2),
                         'non-w'          : round(sum([z.pct_blk,z.pct_hisp]) / float(sum([z.pct_blk, z.pct_hisp, z.pct_white]))*100,2),
                       })
    for row in sorted(data,key = lambda x: x['comp_pct_wkf'], reverse=True):
        outcsv.writerow(row)
    #print str(round(float(len(z.complaint_set.all()))/z.cnt_workforce,4)*100) + '% of workforce complains', \
    #        str(round(sum([z.pct_blk,z.pct_hisp]) / float(sum([z.pct_blk, z.pct_hisp, z.pct_white])),4)*100), '% of pop is hisp/black'
    outfile.close()


def zip_report(year=None,chi=True,zips=zips):
    outfile_name = reports_dir + 'zip_report.csv'
    if chi: outfile_name = reports_dir + 'zip_report_chi.csv'
    outfile = open(outfile_name,'w')
    outcsv = csv.DictWriter(outfile,
        ['zip','pct_wht','pct_hisp','pct_blk','pct_non-wht','pct_frn_brn','pct_poor',
        'comp_count*','wkf_count','comp_rate_by_wkf','paid_count','dism_count','paid_rate','dism_rate'])
    outcsv.writeheader()
    if chi: 
        chi_zips = [z for z in zips if z.zip_code in chicago_zip_codes]
        zips = chi_zips
    rows = []
    for zip in zips:
        wc_complaints_all = [x for x in zip.complaint_set.all() if x.case_type == 'wc']
        if year:
            wc_complaints = [x for x in wc_complaints_all if x.date_filed and x.date_filed.year == year]
        else:
            wc_complaints = wc_complaints_all
        wc_paid = [x for x in wc_complaints if x.status == 'Paid']
        wc_dismissed = [x for x in wc_complaints if x.status == 'Dismissed']
        paid_rate = round(len(wc_paid)/float(len(wc_complaints))*100,2) if wc_complaints else 'NA'
        dism_rate = round(len(wc_dismissed)/float(len(wc_complaints))*100,2) if wc_complaints else 'NA'
        row = {
                'zip':zip.zip_code,
                'pct_wht':zip.pct_white,
                'pct_hisp':zip.pct_hisp,
                'pct_blk':zip.pct_blk,
                'pct_non-wht':100-zip.pct_white,
                'pct_frn_brn':zip.pct_frn_born,
                'pct_poor':zip.pct_poverty,
                'comp_count*':len(wc_complaints),
                'wkf_count':zip.cnt_workforce,
                'comp_rate_by_wkf':round(len(wc_complaints)/float(zip.cnt_workforce)*100,2),
                'paid_count': len(wc_paid),
                'dism_count': len(wc_dismissed),
                'paid_rate': paid_rate,
                'dism_rate': dism_rate,
              }
        rows.append(row)
    for row in sorted(rows, key = lambda x: x['comp_rate_by_wkf'], reverse = True):
        outcsv.writerow(row)
    outfile.write('\r\n*complaint counts include wage complaints (and not min wage complaints)')
    outfile.write('\r\ncomplaint rate denominators include all cases for year ' + str(year))
    outfile.close()
