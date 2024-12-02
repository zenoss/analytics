var exampleTestSuite = new YAHOO.tool.TestSuite("Example Suite");
exampleTestSuite.add(new YAHOO.tool.TestCase({ 
  
     name: "Example TestCase", 
      
     testDataTypeAsserts : function () { 
         var Assert = YAHOO.util.Assert; 
          
         Assert.isString("Hello world");     //passes 
         Assert.isNumber(1);                 //passes 
         Assert.isArray([]);                 //passes 
         Assert.isObject([]);                //passes 
         Assert.isFunction(function(){});    //passes 
         Assert.isBoolean(true);             //passes 
         Assert.isObject(function(){});      //passes 

         Assert.isNumber("1", "Value should be a number.");  //fails 
         Assert.isString(1, "Value should be a string.");    //fails 
     } 
 })); 

// Add the suite to the global test runner
YAHOO.tool.TestRunner.add(exampleTestSuite);

// Tell YUILoader we're ready to run this one
YAHOO.register("test_example", YAHOO.zenoss, {});
