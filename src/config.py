# config.py

from pathlib import Path

# project root
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# resource directories
ASSETS_DIR      = PROJECT_ROOT / "assets"
OUTPUT_DIR      = Path.home() / "Desktop"
CACHE_DIR       = PROJECT_ROOT / "output" / "cache"
LOG_FILE        = PROJECT_ROOT / "output" / "scraper.log"
PERSISTENCE_DIR = PROJECT_ROOT / "persistence"
HIDDEN_IDS_FILE = PERSISTENCE_DIR / "hidden_ids.json"

# output
OUTPUT_FILENAME_PREFIX = "rfp_scraping_output_"
OUTPUT_FILE_EXTENSION   = ".xlsx"

# scraper config folder
SCRAPER_DIR   = PROJECT_ROOT / "src" / "scraper"
KEYWORDS_FILE = SCRAPER_DIR / "keywords.txt"

# defaults
DEFAULT_TIMEOUT   = 30
USER_AGENT        = "RFP-Scraper/1.0"
SELENIUM_HEADLESS = False
MAX_RETRIES       = 3
MAX_CACHE_FILES = 5

from pathlib import Path
STATE_RFP_URL_MAP = {
    "alabama": 'https://procurement.staars.alabama.gov/PRDVSS1X1/AltSelfService',
    "arkansas": 'https://arbuy.arkansas.gov/bso/view/search/external/advancedSearchBid.xhtml?openBids=true',
    "arizona": 'https://app.az.gov/page.aspx/en/rfp/request_browse_public',
    "california": 'https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx',
    "colorado": 'https://prd.co.cgiadvantage.com/PRDVSS1X1/Advantage4',
    "connecticut": 'https://portal.ct.gov/das/ctsource/bidboard?language=en_US',
    "district of columbia": 'https://contracts.ocp.dc.gov/solicitations/search',
    "delaware": 'https://mmp.delaware.gov/Bids/',
    "florida": 'https://vendor.myfloridamarketplace.com/mfmp/pub/search/bids',
    "georgia": 'https://ssl.doas.state.ga.us/gpr/eventSearch',
    "hawaii": 'https://hiepro.ehawaii.gov/welcome.html',
    "iowa": 'https://bidopportunities.iowa.gov/Home/DT_HostedBidsSearch',
    "idaho": 'https://sms-idaho-prd.tam.inforgov.com/fsm/SupplyManagementSupplier/list/SourcingEvent.XiOpenForBid?navigation=SourcingEvent%5BByCompany%5D%28_niu_,_niu_%29.OpenEventsNav&csk.SupplierGroup=LUMA',
    "illinois": 'https://www.bidbuy.illinois.gov/bso/view/search/external/advancedSearchBid.xhtml?openBids=true',
    "indiana": 'https://www.in.gov/idoa/procurement/current-business-opportunities/',
    "kansas": 'https://supplier.sok.ks.gov/psc/sokfsprdsup/SUPPLIER/ERP/c/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL',
    "kentucky": 'https://vss.ky.gov/vssprod-ext/Advantage4',
    "louisiana": 'https://wwwcfprd.doa.louisiana.gov/osp/lapac/srchopen.cfm?deptno=all&catno=all&dateStart=&dateEnd=&compareDate=O&keywords=&keywordsCheck=all',
    "massachusetts": 'https://www.commbuys.com/bso/view/search/external/advancedSearchBid.xhtml?openBids=true',
    "maryland": 'https://emma.maryland.gov/page.aspx/en/rfp/request_browse_public',
    "maine": 'https://www.maine.gov/dafs/bbm/procurementservices/vendors/rfps',
    "michigan": 'https://sigma.michigan.gov/PRDVSS1X1/Advantage4',
    "minnesota": 'https://osp.admin.mn.gov/GS-auto',
    "missouri": 'https://ewqg.fa.us8.oraclecloud.com/fscmUI/redwood/negotiation-abstracts/view/abstractlisting?prcBuId=300000005255687',
    "mississippi": 'https://www.ms.gov/dfa/contract_bid_search/Bid/BidData?AppId=1',
    "montana": 'https://bids.sciquest.com/apps/Router/PublicEvent?CustomerOrg=StateOfMontana',
    "north carolina": 'https://evp.nc.gov/solicitations/',
    "north dakota": "https://apps.nd.gov/csd/spo/services/bidder/searchSolicitation.do?path=%2Fbidder%2FsearchSolicitation&command=searchSearchSolicitation&selectedSolicitation=&searchDT.solNo=&searchDT.agency=&searchDT.officer=&searchDT.keyword=&",
    "nebraska": 'https://das.nebraska.gov/materiel/bid-opportunities.html',
    "new hampshire": 'https://apps.das.nh.gov/bidscontracts/bids.aspx',
    "new jersey": 'https://www.njstart.gov/bso/view/search/external/advancedSearchBid.xhtml?openBids=true',
    "new mexico": 'https://bids.sciquest.com/apps/Router/PublicEvent?CustomerOrg=StateOfNewMexico&tab=PHX_NAV_SourcingOpenForBid&tmstmp=',
    "nevada": 'https://nevadaepro.com/bso/view/search/external/advancedSearchBid.xhtml?openBids=true',
    "new york": 'https://ogs.ny.gov/procurement/bid-opportunities',
    "ohio": 'https://ohiobuys.ohio.gov/page.aspx/en/rfp/request_browse_public',
    "oregon": 'https://oregonbuys.gov/bso/view/search/external/advancedSearchBid.xhtml?openBids=true',
    "pennsylvania": 'https://www.emarketplace.state.pa.us/Search.aspx',
    "rhode island": 'https://webprocure.proactiscloud.com/wp-full-text-search/search/sols?customerid=46&q=*&from=0&sort=r&f=ps=Open&oids=',
    "south carolina": 'https://scbo.sc.gov/search',
    "south dakota": 'https://postingboard.esmsolutions.com/api/postingBoard/3444a404-3818-494f-84c5-2a850acd7779/currentevents',
    "texas": 'https://www.txsmartbuy.gov/app/extensions/CPA/CPAMain/1.0.0/services/ESBD.Service.ss?c=852252&n=2',
    "utah": 'https://utah.bonfirehub.com/PublicPortal/getOpenPublicOpportunitiesSectionData',
    "virginia": 'https://mvendor.cgieva.com/Vendor/public/AllOpportunities.jsp',
    "vermont": 'https://www.vermontbusinessregistry.com/BidSearch.aspx?type=1',
    "washington": 'https://pr-webs-vendor.des.wa.gov/BidCalendar.aspx',
    "wisconsin": 'https://esupplier.wi.gov/psp/esupplier_6/SUPPLIER/ERP/c/WI_SS_SELF_SERVICE.WI_SS_BIDDER_BIDS.GBL?Page=WI_SS_BIDDER_BIDS&Action=U',
    "west virginia": 'https://prd311.wvoasis.gov/PRDVSS1X1ERP/Advantage4',
    "wyoming": 'https://www.publicpurchase.com/gems/wyominggsd,wy/buyer/public/publicInfo'
}

COUNTY_RFP_URL_MAP = {
    "arizona": {
        "maricopa": 'https://www.bidnetdirect.com/arizona/maricopacounty?srchoid_override=217285&posting=1&curronly=1',
        "pima": 'https://www.bidnetdirect.com/arizona/pimacounty',
    },
    "california": {
        "alameda": 'https://api.procurement.opengov.com/api/v1/government/acgov/project/public',
        "contra costa": 'https://www.bidnetdirect.com/california/contracostacounty',
        "los angeles": 'https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList',
        "orange": 'https://api.procurement.opengov.com/api/v1/government/ocgov/project/public',
        "sacramento": 'https://api.procurement.opengov.com/api/v1/government/saccounty/project/public',
        "san bernadino": 'https://epro.sbcounty.gov/bso/view/search/external/advancedSearchBid.xhtml?openBids=true',
        "santa clara": 'https://api.biddingousa.com/restapi/bidding/list/noauthorize/1/41284411',
        "san diego": 'https://sdbuynet.sandiegocounty.gov/page.aspx/en/rfp/request_browse_public'
    },
    "florida": {
        "broward": 'https://broward.bonfirehub.com/PublicPortal/getOpenPublicOpportunitiesSectionData?_=',
        "hillsborough": 'https://hillsboroughcounty.bonfirehub.com/PublicPortal/getOpenPublicOpportunitiesSectionData?_=',
        "orange": 'https://api.procurement.opengov.com/api/v1/government/orangecountyfl/project/public',
        "palm beach": 'https://pbcvssp.pbc.gov/vssprd/Advantage4',
    },
    "georgia": {
        "fulton": 'https://www.bidnetdirect.com/georgia/fultoncounty',
        "gwinnett": 'https://www.gwinnettcounty.com/departments/financialservices/purchasing/bidsandrfps',
    },
    "illinois": {
        "cook": 'https://cookcountyil.bonfirehub.com/PublicPortal/getOpenPublicOpportunitiesSectionData?_=',
    },
    "massachusetts": {
        "middlesex": 'https://api.procurement.opengov.com/api/v1/government/cambridgema/project/public',
    },
    "maryland": {
        "montgomery": 'https://www.bidnetdirect.com/maryland/montgomerycounty',
    },
    "michigan": {
        "oakland": 'https://www.bidnetdirect.com/mitn/oakland-county',
        "wayne": 'https://www.bidnetdirect.com/mitn/county-of-wayne',
    },
    "minnesota": {
        "hennepin": 'https://supplier.hennepin.us/psc/fprd/SUPPLIER/ERP/c/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL?&',
    },
    "north carolina": {
        "mecklenburg": 'https://mecknc-vss.hostams.com/PRDVSS1X1/Advantage4',
        "wake": 'https://wake.bonfirehub.com/PublicPortal/getOpenPublicOpportunitiesSectionData?_='
    },
    "nevada": {
        "clark": 'https://api.demandstar.com/contents/agency/search?id=e43ae9f5-b03b-400b-87ba-874dedef1951',
    },
    "new york": {
        "every": 'https://a0333-passportpublic.nyc.gov/rfx.html',
    },
    "ohio": {
        "cuyahoga": 'https://ccprod-lm01.cloud.infor.com:1442/lmscm/SourcingSupplier/list/SourcingEvent.OpenForBid?sortOrderName=SourcingEvent.SymbolicKey&fk=SourcingEvent(10,4080)&csk.CHP=LMPROC&hasNext=false&menu=EventManagement.BrowseOpenEvents&previousDisabled=true&pageop=load&pagesize=200&csk.SupplierGroup=CUYA&hasPrevious=false&rk=SourcingEvent(_niu_,_niu_)&isAscending=true&lk=SourcingEvent(10,6572)',
        "franklin": 'https://bids.franklincountyohio.gov/table.cfm',
    },
    "pennsylvania": {
        "allegheny": 'https://solicitations.alleghenycounty.us/',
        "philadelphia": 'https://philawx.phila.gov//ECONTRACT/Documents/FrmOpportunityList.aspx',
    },
    "texas": {
        "bexar": 'https://bexarprod-lm01.cloud.infor.com:1442/lmscm/SourcingSupplier/list/SourcingEvent.OpenForBid?csk.CHP=LMPROC&csk.SupplierGroup=100&fk=SourcingEvent(100,1185)&lk=SourcingEvent(100,1188)&rk=SourcingEvent(_niu_,_niu_)&pageSize=20&pageop=load&menu=EventManagement.BrowseOpenEvents',
    }
}

AVAILABLE_STATES = list(STATE_RFP_URL_MAP.keys())
AVAILABLE_COUNTIES_BY_STATE = {
    state: list(counties.keys())
    for state, counties in COUNTY_RFP_URL_MAP.items()
}

FALLBACK_CSRF = "4b9qnD7UgwevuI79WCsBUAv2VtsgEvdqW8gdWmgRSO0%3D"
KEYWORD_FILE = './scraper/config/keywords.txt'

BUSINESS_UNIT_DICT = {'Statewide Business Unit': '0000', 'State of California Emergency': '00001', 'Major Revenue - DOF USE ONLY': '0001', 'Major Policy Revenue - DOF USE': '0003', 'Legislative/Judicial/Executive': '0010', 'Legislative': '0020', 'Legislature': '0100', 'Senate': '0110', 'Assembly': '0120', 'Legislative Joint Expenses': '0130', "Contrib Legislatrs' Retire Sys": '0150', 'Legislative Counsel Bureau': '0160', 'Judicial': '0200', 'CA Judicial Center Library': '0240', 'Judicial Branch': '0250', 'SUPREME COURT': '0260', 'JUDICIAL COUNCIL': '0270', 'Comm. on Judicial Performance': '0280', 'Habeas Resource Center': '0290', 'DISTRICT COURTS OF APPEAL': '0300', '1st DISTRICT COURT OF APPEAL': '0310', '2nd DISTRICT COURT OF APPEAL': '0320', '3rd DISTRICT COURT OF APPEAL': '0330', "Judges' Retirement System": '0390', 'Executive': '0490', "Governor's Office": '0500', 'California Technology Agency': '0502', 'Business & Economic Developmnt': '0509', 'Sec. for State & Consumer Svcs': '0510', "Sec., Gov't Operations Agency": '0511', 'Bus, Consmer Svcs & Hsng Secty': '0515', 'Sec Business Trans & Housing': '0520', 'Sec., Transportation Agency': '0521', 'Sec., Health & Human Services': '0530', 'Ofc Technology and Solutions I': '0531', 'Sec., Natural Resources': '0540', 'Inspector General Office': '0552', 'Sec., Environment Protection': '0555', 'Secretary for Education': '0558', 'Sec., Labor/Workforce Develop': '0559', 'Wellness & Physical Fitness': '0570', 'Service & Volunteering Agency': '0596', "Gov's Off of Lnd Use & Clmt In": '0650', 'Gov Ofc Serv and Community Eng': '0680', 'Office of Emergency Services': '0690', "Governor's Portrait": '0720', 'Governor Elect & Outgoing': '0730', 'Executive/Constitutional': '0740', 'Office of Lieutenant Governor': '0750', 'Rural Youth Employment Comm': '0780', 'Department of Justice': '0820', 'State Controller': '0840', 'Department of Insurance': '0845', 'CA State Lottery Commission': '0850', 'CA Gambling Control Commission': '0855', 'State Board of Equalization': '0860', 'Office of Tax Appeals': '0870', 'Secretary of State': '0890', 'Citizens Redistricting Comm': '0911', 'State Treasurer': '0950', 'Scholarshare Investment Board': '6054', 'Debt & Investment Advisory Com': '0956', 'HOPE for Children Trust Acct': '0957', 'Debt Limit Allocation Commitee': '0959', 'Transportation Financing Auth': '0964', 'Industrial Develop Fin Comm': '0965', 'Tax Credit Allocation Commitee': '0968', 'Alternative Energy & Adv Trans': '0971', 'Sacramento City Fin Auth': '0972', 'Riverside Cty Public Fin Auth': '0973', 'Pollution Control Fin Auth': '0974', 'Los Angeles State Bldg Auth': '0975', 'Capitol Area Development Auth': '0976', 'Health Facilities Fin Auth': '0977', 'San Francisco State Bldg Auth': '0978', 'Oakland Joint Powers Authority': '0979', 'California ABLE Act Board': '0981', 'Urban Waterfront Area Restore': '0983', 'CalSavers Retirement Savings B': '0984', 'CA School Finance Authority': '0985', 'Educational Facilities Auth': '0989', 'GO Bonds - Debt Service - LJE': '0996', 'Business, Consumer Srvs & Hous': '1000', 'Sec., Biz, Con Srvs, & Housing': '1015', 'No Subagency - DO NOT USE': '5220', 'Sec., State & Consumer Service': '1030', 'Cannabis Control Appeals Panel': '1045', 'CA Science Center': '1100', 'CA African¿American Museum': '1105', 'Consumer Affairs-Reg Boards': '1110', 'Department of Consumer Affairs': '1111', 'Department of Cannabis Control': '1115', 'A. E. Alquist Seismic Safety': '1690', 'Civil Rights Department': '1700', 'Fair Employment and Housing': '17000', 'Dept of Finan Protec and Innov': '1701', 'California Privacy Protection': '1703', 'Fair Employment & Housing Comm': '1705', 'Franchise Tax Board': '1730', 'Horse Racing Board': '1750', 'Department of General Services': '1760', 'Victim Comp & Govt Claims Bd': '1870', 'State Personnel Board': '1880', "Public Employees' Retirement": '1900', "State Teachers' Retirement": '1920', 'GO Bonds - Debt Service\xa0 - BCH': '1996', 'Business, Transport & Housing': '2000', 'Business & Housing': '2010', 'Transportation': '2500', 'Sec., Business, Trans & Housng': '2030', 'Dept. Alcoholic Beverage Cntrl': '2100', 'Alcoholic Beverage Cntl Appeal': '2120', 'Dept. of Financial Institution': '2150', 'Department of Corporations': '2180', 'St Asst Fd Enterprise,Bus & In': '2222', 'Housing & Community Developmnt': '2240', 'CA Housing Finance Agency': '2260', 'Office Real Estate Appraisers': '2310', 'Department of Real Estate': '2320', 'Dept of Managed Health Care': '4150', 'Sec. for Transportation Agency': '2521', 'CA Transportation Commission': '2600', 'State Transit Assistance': '2640', 'Department of Transportation': '2660', 'High Speed Rail Authority': '2665', 'High-Speed Rail Auth Ofc Inspe': '2667', 'Board of Pilot Commissioners': '2670', 'Office of Traffic Safety': '2700', 'Dept of the CA Highway Patrol': '2720', 'Department of Motor Vehicles': '2740', 'GO Bonds-Transportation': '2830', 'Natural Resources': '3000', 'Sec., Natural Resources Agency': '3030', 'Exposition Park': '3100', 'Office of Exposition Park': '31001', 'CA African American Museum': '3105', 'Special Resources Programs': '3110', 'CA Tahoe Conservancy': '3125', 'Geothermal ResourcesDevProgram': '3180', 'Environmental Protection Pgm': '3210', 'CA Conservation Corps': '3340', 'Office of Energy Infrastructur': '3355', 'Energy Resources Conservation': '3360', 'Renew Res Protect Pgm': '3370', 'Colorado River Board of CA': '3460', 'Department of Conservation': '3480', 'Resources Recycling & Recovery': '3970', 'CAL FIRE': '3540', 'State Lands Commission': '3560', 'Department of Fish & Wildlife': '3600', 'Wildlife Conservation Board': '3640', 'Dept of Boating & Waterways': '3680', 'CA Coastal Commission': '3720', 'State Coastal Conservancy': '3760', 'Native American Heritage Comm': '3780', 'Dept of Parks & Recreation': '3790', 'Santa Monica Mtns Conservancy': '3810', 'Salton Sea Conservancy': '3815', 'SF Bay Conservation Commission': '3820', 'San Gabriel & Lower LA Rivers': '3825', 'San Joaquin River Conservancy': '3830', 'Baldwin Hills and Urban Waters': '3835', 'Delta Protection Commission': '3840', 'San Diego River Conservancy': '3845', 'Coachella Valley Mtns Conser': '3850', 'Sierra Nevada Conservancy': '3855', 'Department of Water Resources': '3860', 'Sacramento-San Joaquin Delta': '3875', 'GO Bonds Resources': '3882', 'Delta Stewardship Council': '3885', 'Environmental Protection': '3890', 'Sec., Environmental Protectio': '3895', 'State Air Resources Board': '3900', 'Dept of Pesticide Regulation': '3930', 'State Water Resources Control': '3940', 'Dept. Toxic Substances Control': '3960', "Env'l Health Hazard Assessment": '3980', 'Ofc of Env Health Hazard Asmnt': '39800', 'GO Bonds Env Protect': '3996', 'Health & Human Services': '4000', 'Sec., Health & Human Srvs Agy': '4020', 'Developmental Disabilities': '4100', 'Emergency Medical Service Auth': '4120', 'Health Care Access and Informa': '4140', 'California Department of Aging': '4170', 'Department of Aging': '41700', 'Commission on Aging': '41800', 'CA Senior Legislature': '4185', 'Dept. Alcohol & Drug Programs': '4200', 'First 5 California': '4250', 'State Dept Hlth Care Services': '4260', 'Department of Public Health': '4265', 'Medical Assistance Commission': '4270', 'Managed Risk Medical Insurance': '4280', 'Dept of Developmental Services': '4300', 'Developmental Services - HQ': '4310', 'State Hospitals': '4460', 'Agnews State Hospital': '4330', 'Fairview State Hospital': '4350', 'F. D. Lanterman State Hospital': '4370', 'Porterville State Hospital': '4390', 'Sonoma State Hospital': '4400', 'Northern CA Facility-Yuba City': '4420', 'SO. CA Facility¿Cathedral City': '4430', 'Department of State Hospitals': '4440', 'State Hospitals Sacramento': '4450', 'State Hospital - Atascadero': '4470', 'State Hospital Metropolitan': '4490', 'State Hospital Napa': '4500', 'State Hospital Patton': '4510', 'State Hospital Stockton': '4520', 'State Hospital Vacaville': '4530', 'State Hospital Coalinga': '4540', 'State Hospital Salinas': '4550', 'Behavioral Hlth Svcs Ovrst Acn': '4560', 'Community Srvcs & Development': '4700', 'CA Health Benefit Exchange': '4800', 'Department of Rehabilitation': '5160', 'Dept of Youth and Community Re': '5165', 'Independent Living Council': '5170', 'Dept of Child Support Services': '5175', 'Department of Social Services': '5180', 'State - Local Realignment 1991': '5195', 'State - Local Realignment 2011': '5196', 'GO Bonds -HHS': '5206', 'Misc Adj- HHS': '5209', 'Corrections & Rehabilitation': '5210', 'Dept of Corrections & Rehab': '5225', 'State & Community Corrections': '5227', 'SAFE NGHBORHOODS & SCHOOLS ACT': '5228', 'Local Law Enforcement Services': '5296', 'Trial Court Security 2011': '5396', 'Prison Industry Authority': '5420', 'Local Community Corrections': '5496', 'District Atty & Pub Def Svcs': '5596', 'Juvenile Justice Programs': '5696', 'ELEA Growth Subaccount': '5796', 'Fed Immig Fd Incarc-DCR': '5990', 'GO Bonds-DCR': '5996', 'Education': '6000', 'K-12 Education': '6010', 'Higher Education': '6013', 'Higher Ed ¿ Community Colleges': '6015', 'Higher Ed - UC, CSU, & Other': '6020', 'Secretary for Education, K-12': '6050', 'Department of Education': '6110', 'CA State Library': '6120', 'Education Audit Appeals Panel': '6125', 'Special Schools': '6190', 'CA School for the Blind': '6200', 'Diagnostic School - North CA': '6210', 'Diagnostic School - Central CA': '6220', 'Diagnostic School - So CA': '6230', 'School for the Deaf-Fremont': '6240', 'School for the Deaf-Riverside': '6250', 'State Summer School for Arts': '6255', 'Summer School for the Arts': '62550', 'Diagnostic Centers': '6260', 'State Contributions to STRS': '6300', 'Retire Costs for Comm Coll': '6305', 'CA Career Resource Network': '6330', 'School Facilities Aid Program': '6350', 'Teacher Credentialing Comm': '6360', 'GO Bonds K-12': '6396', 'Postsecondary Education Comm': '6420', 'University of California': '6440', 'Institute for Regenerative Med': '6445', 'UC Office of the President': '6491', 'UC Berkeley': '6500', 'UC Davis': '6510', 'UC Davis Medical Center': '6511', 'UC Irvine': '6520', 'UC Irvine Med Center': '6521', 'UCLA': '6530', 'blankblank': '6540', 'UC San Francisco': '6560', 'UCSF Medical Center': '6561', 'UC Santa Cruz': '6580', 'UC Merced': '6590', 'College of the Law, San Fran': '6600', 'Cal State University': '6610', 'CSU Statewide Programs': '6620', 'CSU Systemwide Offices': '6630', 'CSU Campuses': '6640', 'CSU Health Ben for Ret\xa0 Annuit': '6645', 'CSU, Bakersfield': '6650', 'CSU, San Bernardino': '6660', 'CSU, Stanislaus': '6670'}

# State name (slug) → USPS abbreviation
AVAILABLE_STATE_ABBR: dict[str, str] = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC",
}