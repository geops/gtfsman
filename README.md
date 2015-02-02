# gtfsman

Manage and keep up-to-date large numbers of huge GTFS feeds. Holds cache of feed information to avoid parsing large feeds every time a command is run.

## Usage
```
$ ./gtfsman.py --help
```
## Examples
### Init
```
$ ./gtfsman.py init switzerland http://gtfs.geops.de/dl/gtfs_complete.zip
Downloading http://www.comune.palermo.it/gtfs/amat_feed_gtfs.zip to /var/lib/gtfs/palermo/gtfs.zip (10518 kB)
Extracting zip file /var/lib/gtfs/palermo/gtfs.zip
Setting feed url for /var/lib/gtfs/palermo/gtfs.zip to http://www.comune.palermo.it/gtfs/amat_feed_gtfs.zip
Initialized new feed in /var/lib/gtfs/palermo/gtfs.zip
```
### List
```
$ ./gtfsman.py list
mailand                         12/01/2015  09/02/2015      s   u
fortworth                       01/02/2015  06/06/2015      s   u
trentino_city                   12/06/2014  09/06/2015          u
fivecounties_suntran            01/09/2012  31/12/2015      s   u
bctransit                       27/01/2014  31/12/2015      s   u
hartford                        10/11/2014  18/04/2015      s   u
portugal                        14/12/2014  12/12/2015      s   u
matera                          01/09/2014  31/08/2015      s    
kolumbus                        20/12/2014  27/03/2015      s   u
susono                          02/02/2015  02/05/2015      s   u
sweden                          07/01/2015  14/06/2015      s   u
omaezaki                        02/02/2015  31/03/2015      s   u
paris                           15/01/2015  15/07/2015      s    
canberra                        01/01/2015  28/02/2015      s   u
newjersey_rail                  23/10/2014  20/04/2015      s    
milwaukee_county                04/01/2015  08/03/2015      s   u
```
### Update
```
$ ./gtfsman.py update palermo
Trying to update "palermo"...
Downloading http://www.comune.palermo.it/gtfs/amat_feed_gtfs.zip to /var/lib/gtfs/palermo/gtfs.zip (10518 kB)
Extracting zip file /var/lib/gtfs/palermo/gtfs.zip
Updated palermo
```
or
```
$ ./gtfsman.py update-all
```
### Feed postprocessing
```
$ ./gtfsman.py set-pp palermo 
Enter cmd: echo ***this would postprocess feed {feed_path}
Storing postprocessing cmd for palermo
$ ./gtfsman.py update palermo
Trying to update "palermo"...
Downloading http://www.comune.palermo.it/gtfs/amat_feed_gtfs.zip to /var/lib/gtfs/palermo/gtfs.zip (10518 kB)
Extracting zip file /var/lib/gtfs/palermo/gtfs.zip
===========================
Running postprocess command
===========================
***this would postprocess feed /var/lib/gtfs/palermo
Updated palermo
```
### Show
```
$ ./gtfsman.py show palermo
palermo
data from:       16/09/2014
data until:      31/12/2014
url:             http://www.comune.palermo.it/gtfs/amat_feed_gtfs.zip
has shapes:      Yes
Postprocess cmd: echo ***this would postprocess feed {feed_path}
```
