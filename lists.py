COUNTRY_NAMES = ["Afghanistan", "Albania", "Algerie", "Andorra", "Angola", "Antigua og Barbuda", "Argentina", "Armenia", "Aserbajdsjan", "Austerrike", "Aust-Timor", "Australia"
                 ,"Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgia", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia-Hercegovina", "Botswana", "Brasil", "Brunei", "Bulgaria", "Burkina Faso", "Burma", "Burundi"
                 ,"Canada", "Chile", "Colombia", "Costa Rica", "Cuba"
                 ,"Danmark", "De forente arabiske emirater", "Dei sameinte arabiske emirata", "Den dominikanske republikk", "Den dominikanske republikken", "Den sentralafrikanske republikk", "Den sentralafrikanske republikken", "Djibouti", "Dominica"
                 ,"Ecuador", "Egypt", "Ekvatorial-Guinea", "Elfenbenskysten", "Elfenbeinskysten", "El Salvador", "Eritrea", "Estland", "Eswatini", "Etiopia"
                 ,"Fiji", "Filippinene", "Filippinane", "Finland", "Frankrike"
                 ,"Gabon", "Gambia", "Georgia", "Ghana", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana"
                 ,"Haiti", "Hellas", "Honduras", "Hviterussland"
                 ,"India", "Indonesia", "Irak", "Iran", "Irland", "Island", "Israel", "Italia"
                 ,"Jamaica", "Japan", "Jemen", "Jordan"
                 ,"Kambodsja", "Kamerun", "Kapp Verde", "Kasakhstan", "Kenya", "Kina", "Kirgisistan", "Kiribati", "Komorene", "Komorane", "Kongo", "Kongo-Brazzaville", "Kosovo", "Kroatia", "Kuwait", "Kviterussland", "Kypros"
                 ,"Laos", "Latvia", "Lesotho", "Libanon", "Liberia", "Libya", "Liechtenstein", "Litauen", "Luxemburg", "Luxembourg"
                 ,"Madagaskar", "Malawi", "Malaysia", "Maldivene", "Maldivane", "Mali", "Malta", "Marokko", "Marshalløyene", "Marshalløyane", "Mauritania", "Mauritius", "Mexico", "Mikronesiaføderasjonen", "Moldova", "Monaco", "Mongolia", "Montenegro", "Mosambik", "Myanmar"
                 ,"Namibia", "Nauru", "Nederland", "Nepal", "New Zealand", "Ny-Zealand", "Nicaragua", "Niger", "Nigeria", "Niue", "Nord-Korea", "Nord-Makedonia", "Norge", "Noreg"
                 ,"Oman"
                 ,"Pakistan", "Palau", "Palestina", "Panama", "Papua Ny-Guinea", "Paraguay", "Peru", "Polen", "Portugal"
                 ,"Qatar"
                 ,"Romania", "Russland", "Rwanda"
                 ,"Saint Kitts og Nevis", "St. Kitts og Nevis", "Saint Lucia", "St. Lucia", "Saint Vincent og Grenadinene", "St. Vincent og Grenadinene", "Saint Vincent og Grenadinane", "St. Vincent og Grenadinane", "Salomonøyene", "Salomonøyane", "Samoa", "San Marino", "São Tomé og Príncipe", "Saudi-Arabia", "Senegal", "Serbia", "Seychellene", "Seychellane", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Somalia", "Spania", "Sri Lanka", "Storbritannia", "Sudan", "Surinam", "Sveits", "Sverige", "Syria", "Sør-Afrika", "Sør-Korea", "Sør-Sudan"
                 ,"Tadsjikistan", "Tanzania", "Thailand", "Togo", "Tonga", "Trinidad og Tobago", "Tsjad", "Tsjekkia", "Tunisia", "Turkmenistan", "Tuvalu", "Tyrkia", "Tyskland"
                 ,"Uganda", "Ukraina", "Ungarn", "Uruguay", "USA", "Usbekistan"
                 ,"Vanuatu", "Vatikanstaten", "Venezuela", "Vietnam"
                 ,"Zambia", "Zimbabwe"
                 ,"Østerrike", "Øst-Timor"]

# Maps Stedsnavn admin1 codes to the ones used by Geonames
ADMIN1_MAP = {
    "03": "12", # Oslo
    "11": "14", # Rogaland
    "15": "08", # Møre og Romsdal
    "18": "09", # Nordland - Nordlánnda
    "31": "13", # Østfold
    "32": "01", # Akershus
    "33": "04", # Buskerud
    "34": "34", # Innlandet
    "39": "20", # Vestfold
    "40": "17", # Telemark
    "42": "42", # Agder
    "46": "46", # Vestland
    "50": "21", # Trøndelag - Trööndelage
    "55": "18", # Troms – Romsa – Tromssa
    "56": "05", # Finnmark – Finnmárku – Finmarkku
}

ADMIN2_MAP = {
    "0301": "0301", # Oslo
    "1101": "1101", # Eigersund
    "1103": "1103", # Stavanger
    "1106": "1106", # Haugesund
    "1108": "1108", # Sandnes
    "1111": "1111", # Sokndal
    "1112": "1112", # Lund
    "1114": "1114", # Bjerkreim
    "1119": "1119", # Hå
    "1120": "1120", # Klepp
    "1121": "1121", # Time
    "1122": "1122", # Gjesdal
    "1124": "1124", # Sola
    "1127": "1127", # Randaberg
    "1130": "1130", # Strand
    "1133": "1133", # Hjelmeland
    "1134": "1134", # Suldal
    "1135": "1135", # Sauda
    "1144": "1144", # Kvitsøy
    "1145": "1145", # Bokn
    "1146": "1146", # Tysvær
    "1149": "1149", # Karmøy
    "1151": "1151", # Utsira
    "1160": "1160", # Vindafjord
    "1505": "1505", # Kristiansund
    "1506": "1506", # Molde
    "1508": "1507", # Ålesund
    "1511": "1511", # Vanylven
    "1514": "1514", # Sande
    "1515": "1515", # Herøy
    "1516": "1516", # Ulstein
    "1517": "1517", # Hareid
    "1520": "1520", # Ørsta
    "1525": "1525", # Stranda
    "1528": "1528", # Sykkylven
    "1531": "1531", # Sula
    "1532": "1532", # Giske
    "1535": "1535", # Vestnes
    "1539": "1539", # Rauma
    "1547": "1547", # Aukra
    "1554": "1554", # Averøy
    "1557": "1557", # Gjemnes
    "1560": "1560", # Tingvoll
    "1563": "1563", # Sunndal
    "1566": "1566", # Surnadal
    "1573": "1573", # Smøla
    "1576": "1576", # Aure
    "1577": "1577", # Volda
    "1578": "1578", # Fjord
    "1579": "1579", # Hustadvika
    "1580": "1580", # Haram - Does not exist in admin2Codes.txt
    "1804": "1804", # Bodø
    "1806": "1806", # Narvik
    "1811": "1811", # Bindal
    "1812": "1812", # Sømna
    "1813": "1813", # Brønnøy
    "1815": "1815", # Vega
    "1816": "1816", # Vevelstad
    "1818": "1818", # Herøy
    "1820": "1820", # Alstahaug
    "1822": "1822", # Leirfjord
    "1824": "1824", # Vefsn
    "1825": "1825", # Grane
    "1826": "1826", # Aarborte - Hattfjelldal
    "1827": "1827", # Dønna
    "1828": "1828", # Nesna
    "1832": "1832", # Hemnes
    "1833": "1833", # Rana
    "1834": "1834", # Lurøy
    "1835": "1835", # Træna
    "1836": "1836", # Rødøy
    "1837": "1837", # Meløy
    "1838": "1838", # Gildeskål
    "1839": "1839", # Beiarn
    "1840": "1840", # Saltdal
    "1841": "1841", # Fauske - Fuossko
    "1845": "1845", # Sørfold
    "1848": "1848", # Steigen
    "1851": "1851", # Lødingen
    "1853": "1853", # Evenes - Evenášši
    "1856": "1856", # Røst
    "1857": "1857", # Værøy
    "1859": "1859", # Flakstad
    "1860": "1860", # Vestvågøy
    "1865": "1865", # Vågan
    "1866": "1866", # Hadsel
    "1867": "1867", # Bø
    "1868": "1868", # Øksnes
    "1870": "1870", # Sortland - Suortá
    "1871": "1871", # Andøy
    "1874": "1874", # Moskenes
    "1875": "1875", # Hábmer - Hamarøy
    "3101": "3001", # Halden
    "3103": "3002", # Moss 
    "3105": "3003", # Sarpsborg
    "3107": "3004", # Fredrikstad
    "3110": "3011", # Hvaler
    "3112": "3017", # Råde
    "3114": "3018", # Våler
    "3116": "3015", # Skiptvet
    "3118": "3014", # Indre Østfold
    "3120": "3016", # Rakkestad
    "3122": "3013", # Marker
    "3124": "3012", # Aremark
    "3201": "3024", # Bærum ¤
    "3203": "3025", # Asker
    "3205": "3030", # Lillestrøm
    "3207": "3020", # Nordre Follo
    "3209": "3033", # Ullensaker
    "3212": "3023", # Nesodden
    "3214": "3022", # Frogn
    "3216": "3019", # Vestby
    "3218": "3021", # Ås
    "3220": "3028", # Enebakk
    "3222": "3029", # Lørenskog
    "3224": "3027", # Rælingen
    "3226": "3026", # Aurskog-Høland
    "3228": "3034", # Nes
    "3230": "3032", # Gjerdrum
    "3232": "3031", # Nittedal
    "3234": "3054", # Lunner
    "3236": "3053", # Jevnaker
    "3238": "3036", # Nannestad
    "3240": "3035", # Eidsvoll
    "3242": "3037", # Hurdal
    "3301": "3005", # Drammen
    "3303": "3006", # Kongsberg
    "3305": "3007", # Ringerike
    "3310": "3038", # Hole
    "3312": "3049", # Lier
    "3314": "3048", # Øvre Eiker
    "3316": "3047", # Modum
    "3318": "3046", # Krødsherad
    "3320": "3039", # Flå
    "3322": "3040", # Nesbyen
    "3324": "3041", # Gol
    "3326": "3042", # Hemsedal
    "3328": "3043", # Ål
    "3330": "3044", # Hol
    "3332": "3045", # Sigdal
    "3334": "3050", # Flesberg
    "3336": "3051", # Rollag
    "3338": "3052", # Nore og Uvdal
    "3401": "3401", # Kongsvinger
    "3403": "3403", # Hamar
    "3405": "3405", # Lillehammer
    "3407": "3407", # Gjøvik
    "3411": "3411", # Ringsaker
    "3412": "3412", # Løten
    "3413": "3413", # Stange
    "3414": "3414", # Nord-Odal
    "3415": "3415", # Sør-Odal
    "3416": "3416", # Eidskog
    "3417": "3417", # Grue
    "3418": "3418", # Åsnes
    "3419": "3419", # Våler
    "3420": "3420", # Elverum
    "3421": "3421", # Trysil
    "3422": "3422", # Åmot
    "3423": "3423", # Stor-Elvdal
    "3424": "3424", # Rendalen
    "3425": "3425", # Engerdal
    "3426": "3426", # Tolga
    "3427": "3427", # Tynset
    "3428": "3428", # Alvdal
    "3429": "3429", # Folldal
    "3430": "3430", # Os
    "3431": "3431", # Dovre
    "3432": "3432", # Lesja
    "3433": "3433", # Skjåk
    "3434": "3434", # Lom
    "3435": "3435", # Vågå
    "3436": "3436", # Nord-Fron
    "3437": "3437", # Sel
    "3438": "3438", # Sør-Fron
    "3439": "3439", # Ringebu
    "3440": "3440", # Øyer
    "3441": "3441", # Gausdal
    "3442": "3442", # Østre Toten
    "3443": "3443", # Vestre Toten
    "3446": "3446", # Gran
    "3447": "3447", # Søndre Land
    "3448": "3448", # Nordre Land
    "3449": "3449", # Sør-Aurdal
    "3450": "3450", # Etnedal
    "3451": "3451", # Nord-Aurdal
    "3452": "3452", # Vestre Slidre
    "3453": "3453", # Øystre Slidre
    "3454": "3454", # Vang
    "3901": "3801", # Horten
    "3903": "3802", # Holmestrand
    "3905": "3803", # Tønsberg
    "3907": "3804", # Sandefjord
    "3909": "3805", # Larvik
    "3911": "3811", # Færder
    "4001": "3806", # Porsgrunn
    "4003": "3807", # Skien
    "4005": "3808", # Notodden
    "4010": "3812", # Siljan
    "4012": "3813", # Bamble
    "4014": "3814", # Kragerø
    "4016": "3815", # Drangedal
    "4018": "3816", # Nome
    "4020": "3817", # Midt-Telemark
    "4022": "3820", # Seljord
    "4024": "3819", # Hjartdal
    "4026": "3818", # Tinn
    "4028": "3821", # Kviteseid
    "4030": "3822", # Nissedal
    "4032": "3823", # Fyresdal
    "4034": "3824", # Tokke
    "4036": "3825", # Vinje
    "4201": "4201", # Risør
    "4202": "4202", # Grimstad
    "4203": "4203", # Arendal
    "4204": "4204", # Kristiansand
    "4205": "4205", # Lindesnes
    "4206": "4206", # Farsund
    "4207": "4207", # Flekkefjord
    "4211": "4211", # Gjerstad
    "4212": "4212", # Vegårshei
    "4213": "4213", # Tvedestrand
    "4214": "4214", # Froland
    "4215": "4215", # Lillesand
    "4216": "4216", # Birkenes
    "4217": "4217", # Åmli
    "4218": "4218", # Iveland
    "4219": "4219", # Evje og Hornnes
    "4220": "4220", # Bygland
    "4221": "4221", # Valle
    "4222": "4222", # Bykle
    "4223": "4223", # Vennesla
    "4224": "4224", # Åseral
    "4225": "4225", # Lyngdal
    "4226": "4226", # Hægebostad
    "4227": "4227", # Kvinesdal
    "4228": "4228", # Sirdal
    "4601": "4601", # Bergen
    "4602": "4602", # Kinn
    "4611": "4611", # Etne
    "4612": "4612", # Sveio
    "4613": "4613", # Bømlo
    "4614": "4614", # Stord
    "4615": "4615", # Fitjar
    "4616": "4616", # Tysnes
    "4617": "4617", # Kvinnherad
    "4618": "4618", # Ullensvang
    "4619": "4619", # Eidfjord
    "4620": "4620", # Ulvik
    "4621": "4621", # Voss
    "4622": "4622", # Kvam
    "4623": "4623", # Samnanger
    "4624": "4624", # Bjørnafjorden
    "4625": "4625", # Austevoll
    "4626": "4626", # Øygarden
    "4627": "4627", # Askøy
    "4628": "4628", # Vaksdal
    "4629": "4629", # Modalen
    "4630": "4630", # Osterøy
    "4631": "4631", # Alver
    "4632": "4632", # Austrheim
    "4633": "4633", # Fedje
    "4634": "4634", # Masfjorden
    "4634": "4634", # Masfjorden
}

# TODO: Finish or delete this.
STEDSNAVN_GEONAMES_FEATURE_CODES = {
    "administrativBydel": "PPLX",
    "adressenavn": "ST",
    "adressetilleggsnavn": "ST",
    "allmenning": "",
    "alpinanlegg": "",
    "ankringsplass": "",
    "annenAdministrativInndeling": "",
    "annenBygningForReligionsutøvelse": "",
    "annenIndustri-OgLagerbygning": "",
    "annenKulturdetalj": "",
    "annenTerrengdetalj": "",
    "annenVanndetalj": "",
    "badeplass": "",
    "bakke": "",
    "bakkeVeg": "",
    "bakkeISjø": "",
    "bakketoppISjø": "",
    "banestrekning": "",
    "banke": "",
    "bankeISjø": "",
    "barnehage": "",
    "bassengISjø": "",
    "bekk": "",
    "berg": "",
    "bergverk": "",
    "boligblokk": "",
    "boligfelt": "",
    "bomstasjon": "",
    "borettslag": "",
    "botn": "",
    "bru": "",
    "bruk": "",
    "brygge": "",
    "busstopp": "",
    "by": "",
    "bydel": "",
    "bygdelagBygd": "",
    "byggForJordbrukFiskeOgFangst": "",
    "båe": "",
    "båeISjø": "",
    "båke": "",
    "campingplass": "",
    "dal": "",
    "dalføre": "",
    "dam": "",
    "delAvInnsjø": "",
    "eggISjø": "",
    "eid": "",
    "eidISjø": "",
    "eiendom": "",
    "elv": "",
    "elvemel": "",
    "elvesving": "",
    "eneboligMindreBoligbygg": "",
    "eng": "",
    "fabrikk": "",
    "farledSkipslei": "",
    "fengsel": "",
    "ferjekai": "",
    "ferjestrekning": "",
    "fiskeplassISjø": "",
    "fjell": "",
    "fjellIDagen": "",
    "fjellheis": "",
    "fjellkant": "",
    "fjellkjedeISjø": "",
    "fjellområde": "",
    "fjellside": "",
    "fjelltoppISjø": "",
    "fjord": "",
    "fjordmunning": "",
    "flyplass": "",
    "fløtningsanlegg": "",
    "fonn": "",
    "fornøyelsespark": "",
    "forretningsbygg": "",
    "forsamlingshusKulturhus": "",
    "forskningsstasjon": "",
    "foss": "",
    "fritidsbolig": "",
    "fylke": "",
    "fyllplass": "",
    "fyrlykt": "",
    "fyrstasjon": "",
    "gammelBosettingsplass": "",
    "garasjeHangarbygg": "",
    "gard": "",
    "gass-OljefeltISjø": "",
    "geologiskStruktur": "",
    "gjerde": "",
    "gravplass": "",
    "grend": "",
    "grensemerke": "",
    "grind": "",
    "grotte": "",
    "grunne": "",
    "grunneISjø": "",
    "grunnkrets": "",
    "gruppeAvTjern": "",
    "gruppeAvVann": "",
    "grustakSteinbrudd": "",
    "grøft": "",
    "halvøy": "",
    "halvøyISjø": "",
    "haug": "",
    "havdyp": "",
    "havn": "",
    "havnehage": "",
    "havområde": "",
    "havstrøm": "",
    "hei": "",
    "heller": "",
    "helseinstitusjon": "",
    "historiskBosetting": "",
    "holdeplass": "",
    "holme": "",
    "holmeISjø": "",
    "holmegruppeISjø": "",
    "hotell": "",
    "hylle": "",
    "hylleISjø": "",
    "hyttefelt": "",
    "høl": "",
    "høyde": "",
    "idrettsanlegg": "",
    "idrettshall": "",
    "industriområde": "",
    "innsjø": "",
    "isbre": "",
    "iskuppel": "",
    "jernstang": "",
    "jorde": "",
    "juv": "",
    "kabel": "",
    "kai": "",
    "kanal": "",
    "kilde": "",
    "kirke": "",
    "klakkISjø": "",
    "klopp": "",
    "kommune": "",
    "kontinentalsokkel": "",
    "korallrev": "",
    "kraftgateRørgate": "",
    "kraftledning": "",
    "kraftstasjon": "",
    "krater": "",
    "landingsplass": "",
    "landskapsområde": "",
    "lanterne": "",
    "li": "",
    "lon": "",
    "lysbøye": "",
    "matrikkeladressenavn": "",
    "melkeplass": "",
    "militærtByggAnlegg": "",
    "mo": "",
    "molo": "",
    "moreneryggISjø": "",
    "museumGalleriBibliotek": "",
    "myr": "",
    "nasjon": "",
    "navnegard": "",
    "nes": "",
    "nesISjø": "",
    "nesVedElver": "",
    "offersted": "",
    "oljeinstallasjon": "",
    "oppdrettsanlegg": "",
    "os": "",
    "overett": "",
    "park": "",
    "parkeringsplass": "",
    "pensjonat": "",
    "platåISjø": "",
    "poststed": "",
    "pytt": "",
    "rasISjø": "",
    "rasteplass": "",
    "renneKløftISjø": "",
    "revISjø": "",
    "rygg": "",
    "ryggISjø": "",
    "rørledning": "",
    "rådhus": "",
    "sadelISjø": "",
    "sand": "",
    "senkning": "",
    "serveringssted": "",
    "seterStøl": "",
    "setervoll": "",
    "severdighet": "",
    "sjødetalj": "",
    "sjøvarde": "",
    "sjøstykke": "",
    "skar": "",
    "skiheis": "",
    "skjær": "",
    "skjærISjø": "",
    "skog": "",
    "skogholt": "",
    "skogområde": "",
    "skole": "",
    "skolekrets": "",
    "skredområde": "",
    "skytebane": "",
    "skytefelt": "",
    "slette": "",
    "sluse": "",
    "småbåthavn": "",
    "sokkelISjø": "",
    "sokn": "",
    "soneinndelingTilHavs": "",
    "stake": "",
    "stasjon": "",
    "statistiskTettsted": "",
    "stein": "",
    "sti": "",
    "strand": "",
    "strandISjø": "",
    "stryk": "",
    "stup": "",
    "stø": "",
    "sund": "",
    "sundISjø": "",
    "sykehus": "",
    "søkk": "",
    "søkkISjø": "",
    "taubane": "",
    "tettbebyggelse": "",
    "tettsted": "",
    "tettsteddel": "",
    "tjern": "",
    "topp": "",
    "torg": "",
    "torvtak": "",
    "traktorveg": "",
    "tunnel": "",
    "turisthytte": "",
    "tV-Radio-EllerMobiltelefontårn": "",
    "tømmervelte": "",
    "undersjøiskVegg": "",
    "universitetHøgskole": "",
    "ur": "",
    "utmark": "",
    "utsiktspunkt": "",
    "utstikker": "",
    "vad": "",
    "vaktstasjonBeredsskapsbygning": "",
    "valgkrets": "",
    "vann": "",
    "varde": "",
    "vegbom": "",
    "vegkryss": "",
    "vegstrekning": "",
    "vegsving": "",
    "verneområde": "",
    "vidde": "",
    "vik": "",
    "vikISjø": "",
    "vulkanISjø": "",
    "vågISjø": "",
    "øy": "",
    "øyISjø": "",
    "øygruppe": "",
    "øygruppeISjø": "",
    "øyr": "",
    "ås": "",
}