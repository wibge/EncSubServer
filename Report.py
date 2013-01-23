import datetime
import os
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
import models


class SalesSummary(db.Model):
  date = db.DateProperty()
  subscriptionPlan = db.StringProperty()
  count = db.IntegerProperty()


class Totals():
       def __init__(self, startDate, endDate):
         self.products = {}
         self.count = 0
         self.income = 0
         self.startDate = startDate
         self.endDate = endDate


class ProductTotal():
     def __init__(self, count, income, pricePerUnit):
         self.count = count
         self.income = income
         self.pricePerUnit = pricePerUnit

     def add(self, count, income):
          self.income += income
          self.count += count


def updateTotals(salesSummary, totals):
      if not salesSummary.subscriptionPlan in totals.products:
        totals.products[salesSummary.subscriptionPlan] = ProductTotal(salesSummary.count, salesSummary.income, salesSummary.pricePerUnit)
      else:
        totals.products[salesSummary.subscriptionPlan].add(salesSummary.count, salesSummary.income)
      totals.count += salesSummary.count
      totals.income += salesSummary.income


def pricePerUnitForSubscriptionPlan(subscriptionPlan):
    pricePerUnit = 0.0
    if subscriptionPlan == '1YEARAPPLE':
      pricePerUnit = 70.00
    elif subscriptionPlan == '1YEARCHARGIFY':
      pricePerUnit = 80.00
    elif subscriptionPlan == '1MONTHAPPLE':
      pricePerUnit = 17.50
    elif subscriptionPlan == '1MONTHCHARGIFY':
      pricePerUnit = 20.00
    elif subscriptionPlan == '1MONTHTRIPKIT':
      pricePerUnit = 350.0
    elif subscriptionPlan == 'AEROMILBAGCOUPON':
      pricePerUnit = 80.0
    return pricePerUnit


def getReport():
  salesSummaries = SalesSummary.gql("ORDER BY date DESC").fetch(200)
  currentDate = datetime.datetime.today().replace(hour=0, minute=0, second=0)
  #currentDate = datetime.datetime(2011, 11, 21, 0, 0, 0)
  lastWeek = currentDate - datetime.timedelta(days=7)
  lastMonth = currentDate - datetime.timedelta(days=30)
  lastWeekTotals = Totals(currentDate, lastWeek)
  lastMonthTotals = Totals(currentDate, lastMonth)

  for salesSummary in salesSummaries:
    salesSummary.pricePerUnit = pricePerUnitForSubscriptionPlan(salesSummary.subscriptionPlan)
    salesSummary.income = salesSummary.pricePerUnit * salesSummary.count

    if salesSummary.date >= lastWeek.date():
      updateTotals(salesSummary, lastWeekTotals)
    if salesSummary.date >= lastMonth.date():
      updateTotals(salesSummary, lastMonthTotals)

  template_values = {
    'salesSummaries': salesSummaries,
    'lastWeekTotals': lastWeekTotals,
    'lastMonthTotals': lastMonthTotals,
    }
  path = os.path.join(os.path.dirname(__file__), 'templates/sales_report.html')
  return template.render(path, template_values)


def sales_for_date(now):
  now -= datetime.timedelta(hours=8)

  dayStart = datetime.datetime(now.year, now.month, now.day, 8)
  dayEnd = dayStart + datetime.timedelta(hours=24)
  #logging.error(dayStart)
  #logging.error(dayEnd)
  today = datetime.date(now.year, now.month, now.day)
  salesSummaries = SalesSummary.gql("WHERE date = :1", today).fetch(10)

  if not salesSummaries:
    salesSummaries = []
  for salesSummary in salesSummaries:
    salesSummary.date = today
    salesSummary.count = 0
  subscriptions = models.Subscription.gql("WHERE created > :1 and created < :2", dayStart, dayEnd)
  for sub in subscriptions:
    #logging.error(purchase.appStoreProductID)
    found = False
    for salesSummary in salesSummaries:
      if salesSummary.subscriptionPlan == sub.subscriptionPlan.identifier:
        salesSummary.count += 1
        found = True
    if not found:
      salesSummary = SalesSummary()
      salesSummary.date = today
      salesSummary.count = 1
      salesSummary.subscriptionPlan = sub.subscriptionPlan.identifier
      salesSummaries.append(salesSummary)
  for salesSummary in salesSummaries:
    salesSummary.save()


class UpdateYesterdaysSales(webapp.RequestHandler):
    """tabulates todays sales"""
    def get(self):
      sales_for_date(datetime.datetime.now() - datetime.timedelta(hours=24))

      self.response.out.write(getReport())


class UpdateSales(webapp.RequestHandler):
  """tabulates todays sales"""
  def get(self):
    sales_for_date(datetime.datetime.now())

    self.response.out.write(getReport())


class Report(webapp.RequestHandler):
  """tabulates todays sales"""
  def get(self):
    self.response.out.write(getReport())


class UpdatePastSales(webapp.RequestHandler):

  def get(self):
    date = datetime.datetime.now()
    while True:
      sales_for_date(date)
      date -= datetime.timedelta(hours=24)
    self.response.out.write(getReport())


# ----- mainline ----- #

application = webapp.WSGIApplication([
                                      #('/admin/deleteAll', DeleteAll),
                                      #('/admin/init', InitializeDatabase),

                                      ('/report/updateSales', UpdateSales),
                                      ('/report/updateYesterday', UpdateYesterdaysSales),
                                      ('/report/updateAll', UpdatePastSales),
                                      ('/report', Report)
                                      ],
                                   debug=True)


def main():
  #x = FetchMetarData()
  #x.get()
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
