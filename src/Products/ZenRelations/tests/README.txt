ZenRelations Testing System:

test files are:
testZenRelations.py
testFullZopeZenRelations.py

ZenRelations uses the following schema to perform tests on relationships:
     


       devices           location ----------
       --------------------------| Location |
      | *                      1  ----------
      |
  --------  devices        groups -------
 | Device |----------------------| Group |
  --------  *                  *  -------
   ^   |
   |   | device            interfaces  -------------
   |    ----------------------------<>| IpInterface |
   |       1                     *     -------------
   |
  --------    1               1   -------
 | Server |----------------------| Admin |
  --------  server         admin  -------


To run the tests, enter the Products directory and use the following:
    zopectl test --libdir ZenRelations
