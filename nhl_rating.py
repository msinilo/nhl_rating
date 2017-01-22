import urllib
import httplib2
import re
from operator import itemgetter
import math
import argparse
import logging

# Calculates Elo/Glicko rating for the NHL teams in the 2015/16 regular season.
# Scores retrieved from www.hockey-reference.com
# Elo: https://en.wikipedia.org/wiki/Elo_rating_system
# Glicko2: http://www.glicko.net/glicko/glicko2.pdf

GLICKO_DEFAULT_RATING	= 1500
GLICKO_DEFAULT_RD		= 350
GLICKO_DEFAULT_VOLATILITY = 0.06
LOSS = 0
WIN = 1
DRAW = 0.5

class Game:
	def __init__(self, ta, tb, s, r = GLICKO_DEFAULT_RATING, rd = GLICKO_DEFAULT_RATING):
		self.teamA = ta
		self.teamB = tb
		self.score = s

		# Glicko
		self.ratingB = r
		self.rdB = rd


MONTHS = { "Oct" : 0, "Nov" : 1, "Dec" : 2, "Jan" : 3, "Feb" : 4, "Mar" : 5, "Apr" : 6 }

def GetK(numSamples, rating):
	if numSamples < 10 and rating < 1700:
		return 50

	return 20

def ParseTeam(team, games, firstTeam, year):
	h = httplib2.Http()
	url = 'http://www.hockey-reference.com/teams/' + team + '/' + str(year) + '.html'
	print url

	(resp_headers, content) = h.request(url, "GET")

	lines = content.splitlines()
	allTeams = {}

	for l in lines:
		if l.find("<span class=\"poptip\"") >= 0:
			# WSH (1-0) beat NJD, 5-3
			# WSH (1-1) lost to SJS, 0-5
			m = re.search("\d+\. (\w+) (\d*), " + team + " \(\d+-\d+\) ([a-z ]+) ([A-Z]+)", l)
			if m:
				month = m.group(1)
				day = m.group(2)
				date = MONTHS.get(month) * 31 + int(day)
				dayGames = games.get(date, [])
				otherTeam = m.group(4)

				existingGame = [x for x in dayGames if x.teamB == team]

				if not existingGame:
					scoreString = m.group(3)
					score = DRAW
					if scoreString.find("beat") >= 0:
						score = WIN
					elif scoreString.find("lost") >= 0:
						score = LOSS
					else:
						raise "Couldn't parse a score string: " + scoreString

					dayGames.append(Game(team, otherTeam, score))
					allTeams[otherTeam] = 1
					games[date] = dayGames

	if firstTeam:
		for team, _ in allTeams.iteritems():
			ParseTeam(team, games, False, year)

def G(rd):
	piSqr = math.pi ** 2
	return 1 / ((1 + (3 * pow(rd, 2) / piSqr)) ** 0.5)

def E_u(u, uj, rdj):
	return 1 / (1 + math.exp(-G(rdj) * (u - uj)))

def ToGlickoScale(r, RD):
	c = 173.7178
	return (r - GLICKO_DEFAULT_RATING) / c, RD / c

def FromGlickScale(mu, phi):
	c = 173.7178
	return c * mu + GLICKO_DEFAULT_RATING, c * phi

def G2_NewSigma(sigma, delta, phi, v, tau):
	a = math.log(sigma ** 2)
	deltaSqr = delta * delta
	phiSqr = phi * phi;

	def f(x):
		expx = math.exp(x)
		num = expx * (deltaSqr - phiSqr - v - expx)
		den = 2 * ((phiSqr + v + expx)**2)

		return (num/den) - ((x - a) / (tau**2))

	# Iterative algo
	A = a

	if deltaSqr > phiSqr + v:
		B = math.log(deltaSqr - phiSqr - v)
	else:
		k = 1
		while f(a - k * tau) < 0:
			k = k + 1

		B = a - (k * tau)

	eps = 0.00001
	f_A, f_B = f(A), f(B)
	while abs(B - A) > eps:
		C = A + (A - B) * f_A / (f_B - f_A)
		f_C = f(C)
		if f_C * f_B < 0:
			A, f_A = B, f_B
		else:
			f_A /= 2

		B, f_B = C, f_C

	newSigma = math.exp(1) ** (A/2)
	return newSigma

# Updates ratings for given team (r, RD)/period
# Steps refer to the original Glicko2 paper 
def Glicko2(r, RD, sigma, periodScores, args):

	# Step 2
	mu, phi = ToGlickoScale(r, RD)

	# Steps 3/4
	v = 0
	dv = 0
	for score in periodScores:
		logging.info("Playing " + score.teamB + " - rating: " + str(score.ratingB) + \
			" score " + str(score.score))

		muj, phij = ToGlickoScale(score.ratingB, score.rdB)
		gj = G(phij)
		Euj = E_u(mu, muj, phij)
		logging.info("Expected score: " + str(Euj))
		v += (gj ** 2) * Euj * (1 - Euj)
		dv += gj * (score.score - Euj)

	if len(periodScores) > 0:
		v = 1 / v
		dv *= v

		# Step 5
		s = G2_NewSigma(sigma, dv, phi, v, args.tau)
	else:
		s = sigma

	# Step 6
	phiStar = math.sqrt(phi ** 2 + s ** 2)

	if len(periodScores) > 0:
		newPhi = 1 / math.sqrt(1 / (phiStar**2) + 1/v)
		newMu = mu + (newPhi**2) * (dv/v)
	else:
		newMu = mu
		newPhi = phiStar

	r, RD = FromGlickScale(newMu, newPhi)

	return r, RD, s

def RateGlickoPeriod(periodGames, ratings, rds_sigmas, graphData, args):
	for team, teamGames in periodGames.iteritems():

		ratingA = ratings.get(team, GLICKO_DEFAULT_RATING)
		logging.info(team + " " + str(ratingA))
		rd_s = rds_sigmas.get(team, [GLICKO_DEFAULT_RD, GLICKO_DEFAULT_VOLATILITY])
		mu, phi, s = Glicko2(ratingA, rd_s[0], rd_s[1], teamGames, args)
		logging.info("New rating " + str(mu))
		ratings[team] = mu
		rds_sigmas[team] = [phi, s]

		if args.graph and args.graph == team:
			graphData.append(mu)
	
def RateGlicko(games, args):
	ratings = {}
	rds_sigmas = {}

	periodGames = {}
	sortedGames = sorted(games.iteritems())
	prevPeriod = sortedGames[0][0]

	graphData = []

	periodDuration = args.period_days
	for date, dayGames in sortedGames:
		for g in dayGames:
			scoreB = 1 - g.score

			ratingA = ratings.get(g.teamA, GLICKO_DEFAULT_RATING)
			ratingB = ratings.get(g.teamB, GLICKO_DEFAULT_RATING)
			rdA = rds_sigmas.get(g.teamA, [GLICKO_DEFAULT_RD, 0])[0]
			rdB = rds_sigmas.get(g.teamB, [GLICKO_DEFAULT_RD, 0])[0]

			gameA = Game(g.teamA, g.teamB, g.score, ratingB, rdB)
			teamGames = periodGames.get(g.teamA, [])
			teamGames.append(gameA)
			periodGames[g.teamA] = teamGames

			gameB = Game(g.teamB, g.teamA, scoreB, ratingA, rdA)
			teamGames = periodGames.get(g.teamB, [])
			teamGames.append(gameB)
			periodGames[g.teamB] = teamGames

		if (date - prevPeriod >= periodDuration):
			RateGlickoPeriod(periodGames, ratings, rds_sigmas, graphData, args)
			prevPeriod = date
			periodGames = {}

	# Last period
	RateGlickoPeriod(periodGames, ratings, rds_sigmas, graphData, args)
	#print rds_sigmas

	return ratings, graphData

def RateElo(games, args):

	ratings = {}
	numSamples = {}
	graphData = []

	for date, dayGames in sorted(games.iteritems()):

		for g in dayGames:
			ratingA = ratings.get(g.teamA, 1500)
			ratingB = ratings.get(g.teamB, 1500)
			scoreA = g.score
			scoreB = 1 - g.score

			logging.info(g.teamA + " vs " + g.teamB + " : " + str(g.score))

			expectedScoreA = 1 / (1 + pow(10, (ratingB - ratingA) / 400))
			expectedScoreB = 1 / (1 + pow(10, (ratingA - ratingB) / 400))

			samplesA = numSamples.get(g.teamA, 0) 
			samplesB = numSamples.get(g.teamB, 0) 

			Ka = GetK(samplesA, ratingA)
			Kb = GetK(samplesB, ratingB)

			newRatingA = ratingA + Ka * (scoreA - expectedScoreA)
			newRatingB = ratingB + Kb * (scoreB - expectedScoreB)

			logging.info("ESA: " + str(expectedScoreA) + ", ESB: " + str(expectedScoreB))
			logging.info("Old rating " + g.teamA + ": " + str(ratingA))
			logging.info("Old rating " + g.teamB + ": " + str(ratingB))

			logging.info("New rating " + g.teamA + ": " + str(newRatingA))
			logging.info("New rating " + g.teamB + ": " + str(newRatingB))
			logging.info("----------------------------------")

			ratings[g.teamA] = newRatingA
			ratings[g.teamB] = newRatingB
			numSamples[g.teamA] = samplesA + 1
			numSamples[g.teamB] = samplesB + 1

			if args.graph and (args.graph == g.teamA or args.graph == g.teamB):
				graphData.append(newRatingA if args.graph == g.teamA else newRatingB)

	return ratings, graphData

def PlotCircle(x, y, radius, color):
	tooltip = 2000 - y
	circleData = "<circle cx=\"" + str(x) + "\" cy=\"" + str(y) + "\" r=\"" + str(radius) + \
		"\" style=\"stroke:#006600; fill:#" + color + "\"><title>" + str(tooltip) + "</title></circle>"
	return circleData

def PlotLine(x1, y1, x2, y2):
	return "<line x1=\"" + str(x1) + "\" y1=\"" + str(y1) + "\" x2=\"" + str(x2) + "\" y2=\"" + str(y2) + \
		"\" style=\"stroke:rgb(127,127,127);stroke-width:2\"/>"

parser = argparse.ArgumentParser(prog='nhl_rating', usage='%(prog)s [options]')
parser.add_argument("rating", help="Rating method (Elo or Glicko)")
parser.add_argument("--tau", help="Glicko Tau parameter (usually 0.3-1.2)", default = 0.5, type=float)
parser.add_argument("--period_days", help="Days/Glicko period", default=12, type=int)
parser.add_argument("--graph", help="Graph rating for given team")
parser.add_argument("--verbose", help="Verbose logging", action='store_true')
parser.add_argument("--year", help="Season", type=int, default=2016)
args = parser.parse_args()

if args.verbose:
	logging.basicConfig(level=logging.INFO)

# Dictionary indexed by dates (ie. Oct 10, Nov 5)
games = {}
teamNames = { 	"TBL", "OTT", "MTL", "FLA", "BOS", "TOR", "BUF", "DET", "STL", "CHI", "DAL", "COL", \
				"MIN", "WPG", "NSH", "WSH", "PIT", "NYR", "PHI", "NJD", "NYI", "CAR", "CBJ", "EDM", \
				"SJS", "VAN", "CGY", "ARI", "ANA", "LAK" }

for t in teamNames:
	ParseTeam(t, games, False, args.year)

ratingFunc = RateElo if args.rating.upper() == "ELO" else RateGlicko

ratings, graphData = ratingFunc(games, args)

for team, score in sorted(ratings.iteritems(), key = itemgetter(1), reverse=True):
	print team + " - " + str(int(score))

if args.graph:

	graphData = [2000 - x for x in graphData]

	plotData = "<svg xmlns=\"http://www.w3.org/2000/svg\" version=\"1.1\" width=\"2000\" height=\"2000\">"

	index = 0
	x = 20;
	PERIOD_X = 10
	while index < len(graphData) - 1:

		nextIndex = index + 1

		lineData = PlotLine(x, graphData[index], x + PERIOD_X, graphData[nextIndex])
		plotData += "\n" + lineData
		plotData += "\n" + PlotCircle(x, graphData[index], 2, "#00cc00")

		index = nextIndex
		x += PERIOD_X

	plotData += "\n</svg>\n"
	with open(args.graph + ".svg", "w") as textFile:
		textFile.write(plotData)

