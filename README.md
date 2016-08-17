Python script calculating Elo/Glicko rating for the NHL teams in the 2015/16 regular season.  
Scores retrieved from www.hockey-reference.com  
Elo: https://en.wikipedia.org/wiki/Elo_rating_system  
Glicko2: http://www.glicko.net/glicko/glicko2.pdf  
  
### Elo:  
PIT - 1654  
STL - 1634    
WSH - 1625  
DAL - 1605  
ANA - 1591  
FLA - 1574  
NYR - 1572  
LAK - 1571  
NYI - 1570  
PHI - 1567  
SJS - 1566  
TBL - 1560  
CHI - 1557  
NSH - 1545  
BOS - 1529  
DET - 1524  
OTT - 1507  
NJD - 1501  
BUF - 1500  
CBJ - 1500  
COL - 1496  
MIN - 1496  
MTL - 1495  
WPG - 1488  
CAR - 1478  
CGY - 1470  
ARI - 1464  
VAN - 1442  
EDM - 1438  
TOR - 1431  
  
### Glicko:  
PIT - 1618  
WSH - 1617  
STL - 1608  
DAL - 1577  
ANA - 1577  
FLA - 1557  
NYR - 1552  
LAK - 1551  
NYI - 1551  
TBL - 1546  
SJS - 1544  
CHI - 1541  
PHI - 1535  
BOS - 1515  
NSH - 1514  
DET - 1504  
NJD - 1481  
OTT - 1481  
COL - 1480  
CBJ - 1479  
BUF - 1471  
MIN - 1465  
MTL - 1462  
CAR - 1452  
WPG - 1451  
CGY - 1447  
ARI - 1437  
EDM - 1415  
VAN - 1412  
TOR - 1409  
  
***Lowest rated team that made the playoffs***: Minnesota  
***Highest rated team that did not make the playoffs***: Boston  
Glicko RDs are all in the 53.5 - 56.5 range  
Both systems 'predicted' playoffs outcomes with the same accuracy - 10/15 series correct (using regular season ratings, not updating based on playoff scores). San Jose was the most surprising, they defeated higher rated teams twice (LAK & STL).  
Glicko period was set to 4 days, otherwise it'd react to changes too slowly. This is much shorter than recommended period (should be 5-10 games), but our sample size is small (82 games).
