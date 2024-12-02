/*****************************************************************************
 * 
 * Portions copyright (C) Zenoss, Inc. 2007, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/
/*****************************************************************************
 * 
 * Portions copyright (C) Julian Robichaux 2007, all rights reserved.
 * 
 * datePicker.js, version 1.5.1 http://www.nsftools.com
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of datePicker and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * 
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 * 
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USER OR OTHER DEALINGS IN THE
 * SOFTWARE.
 * 
 ****************************************************************************/


var datePickerDivID = "datepicker";
var iFrameDivID = "datepickeriframe";

var dayArrayShort = new Array('Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa');
var dayArrayMed = new Array('Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat');
var dayArrayLong = new Array('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday');
var monthArrayShort = new Array('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec');
var monthArrayMed = new Array('Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec');
var monthArrayLong = new Array('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December');

var defaultDateSeparator = "/";        // common values would be "/" or "."
var defaultDateFormat = "mdy"    // valid values are "mdy", "dmy", and "ymd"
var dateSeparator = defaultDateSeparator;
var dateFormat = defaultDateFormat;

var dateRangesList = new Array();

function addDateRange(startDateFieldName, endDateFieldName, startDateField, endDateField) {
    var startField = startDateField?startDateField:document.getElementsByName(startDateFieldName).item(0),
        endField = endDateField?endDateField:document.getElementsByName(endDateFieldName).item(0),
        range = {
        'startDate': {
            'name': startDateFieldName,
            'obj': startField
        },
        'endDate': {
            'name': endDateFieldName,
            'obj': endField
        }
    }

    // use user date format;
    userDateFormat(startField);
    userDateFormat(endField);
    var el = startField;
    while(el && el.nodeName.toLowerCase() !== 'form') {
        el = el.parentNode;
    }
    if (el) {
        // before form submit we should convert date formats to server friendly formats
        el.onsubmit = function() {
            startField.value = getDateString(startField.dateValue);
            endField.value = getDateString(endField.dateValue);
            return true;
        };
    }

    dateRangesList.push(range);
}

function userDateFormat(el) {
    var parentWin = window.parent;
    if (parentWin) {
        var dateFormat = parentWin.Zenoss.USER_DATE_FORMAT,
            val = el.value,
            date = getFieldDate(val);

        el.value = parentWin.Zenoss.render.date(date, dateFormat);
        // store date object in field to use it later;
        el.dateValue = date;
    }
}

function isValidDate(dateFieldName, dateString) {
    var dateObj = getFieldDate(dateString);

    for (var i in dateRangesList ) {
        var dateRange = dateRangesList[i];

        if (dateFieldName == dateRange['startDate']['name']) {
            return dateObj <= dateRange['endDate']['obj'].dateValue;
        }else if (dateFieldName == dateRange['endDate']['name']) {
            return dateObj >= dateRange['startDate']['obj'].dateValue;
        }
    }

    return true;
}
function displayDatePicker(dateFieldName, displayBelowThisObject, dtFormat, dtSep)
{
  var targetDateField = document.getElementsByName (dateFieldName).item(0);

  // if we weren't told what node to display the datepicker beneath, just display it
  // beneath the date field we're updating
  if (!displayBelowThisObject)
	displayBelowThisObject = targetDateField;

  // if a date separator character was given, update the dateSeparator variable
  if (dtSep)
	dateSeparator = dtSep;
  else
	dateSeparator = defaultDateSeparator;

  // if a date format was given, update the dateFormat variable
  if (dtFormat)
	dateFormat = dtFormat;
  else
	dateFormat = defaultDateFormat;

  var x = displayBelowThisObject.offsetLeft;
  var y = displayBelowThisObject.offsetTop + displayBelowThisObject.offsetHeight ;

  // deal with elements inside tables and such
  var parent = displayBelowThisObject;
  while (parent.offsetParent) {
	parent = parent.offsetParent;
	x += parent.offsetLeft;
	y += parent.offsetTop ;
  }

  drawDatePicker(targetDateField, x, y);
}

function drawDatePicker(targetDateField, x, y)
{
  // var dt = getFieldDate(targetDateField.value );
  var dt = targetDateField.dateValue;

  if (!document.getElementById(datePickerDivID)) {
	var newNode = document.createElement("div");
	newNode.setAttribute("id", datePickerDivID);
	newNode.setAttribute("class", "dpDiv");
	newNode.setAttribute("style", "visibility: hidden;");
	document.body.appendChild(newNode);
  }

  var pickerDiv = document.getElementById(datePickerDivID);
  pickerDiv.style.position = "absolute";
  pickerDiv.style.left = x + "px";
  pickerDiv.style.top = y + "px";
  pickerDiv.style.visibility = (pickerDiv.style.visibility == "visible" ? "hidden" : "visible");
  pickerDiv.style.display = (pickerDiv.style.display == "block" ? "none" : "block");
  pickerDiv.style.zIndex = 10000;

  // draw the datepicker table
  refreshDatePicker(targetDateField.name, dt.getFullYear(), dt.getMonth(), dt.getDate());
}


function refreshDatePicker(dateFieldName, year, month, day)
{
  var thisDay = new Date();

  if ((month >= 0) && (year > 0)) {
	thisDay = new Date(year, month, 1);
  } else {
	day = thisDay.getDate();
	thisDay.setDate(1);
  }

  var crlf = "\r\n";
  var TABLE = "<table cols=7 class='dpTable'>" + crlf;
  var xTABLE = "</table>" + crlf;
  var TR = "<tr class='dpTR'>";
  var TR_title = "<tr class='dpTitleTR'>";
  var TR_days = "<tr class='dpDayTR'>";
  var TR_todaybutton = "<tr class='dpTodayButtonTR'>";
  var xTR = "</tr>" + crlf;
  var TD = "<td class='dpTD' onMouseOut='this.className=\"dpTD\";' onMouseOver=' this.className=\"dpTDHover\";' ";    // leave this tag open, because we'll be adding an onClick event
  var TD_title = "<td colspan=5 class='dpTitleTD'>";
  var TD_buttons = "<td class='dpButtonTD'>";
  var TD_todaybutton = "<td colspan=7 class='dpTodayButtonTD'>";
  var TD_days = "<td class='dpDayTD'>";
  var TD_selected = "<td class='dpDayHighlightTD' onMouseOut='this.className=\"dpDayHighlightTD\";' onMouseOver='this.className=\"dpTDHover\";' ";    // leave this tag open, because we'll be adding an onClick event
  var xTD = "</td>" + crlf;
  var DIV_title = "<div class='dpTitleText'>";
  var DIV_selected = "<div class='dpDayHighlight'>";
  var xDIV = "</div>";

  // start generating the code for the calendar table
  var html = TABLE;

  // this is the title bar, which displays the month and the buttons to
  // go back to a previous month or forward to the next month
  html += TR_title;
  html += TD_buttons + getButtonCode(dateFieldName, thisDay, -1, "&lt;") + xTD;
  html += TD_title + DIV_title + monthArrayLong[ thisDay.getMonth()] + " " + thisDay.getFullYear() + xDIV + xTD;
  html += TD_buttons + getButtonCode(dateFieldName, thisDay, 1, "&gt;") + xTD;
  html += xTR;

  // this is the row that indicates which day of the week we're on
  html += TR_days;
  for(i = 0; i < dayArrayShort.length; i++)
	html += TD_days + dayArrayShort[i] + xTD;
  html += xTR;

  // now we'll start populating the table with days of the month
  html += TR;

  // first, the leading blanks
  for (i = 0; i < thisDay.getDay(); i++)
	html += TD + "&nbsp;" + xTD;

  // now, the days of the month
  do {
	dayNum = thisDay.getDate();
	TD_onclick = " onclick=\"updateDateField('" + dateFieldName + "', '" + getDateString(thisDay) + "');\">";

	if (dayNum == day)
	  html += TD_selected + TD_onclick + DIV_selected + dayNum + xDIV + xTD;
	else
	  html += TD + TD_onclick + dayNum + xTD;

	// if this is a Saturday, start a new row
	if (thisDay.getDay() == 6)
	  html += xTR + TR;

	// increment the day
	thisDay.setDate(thisDay.getDate() + 1);
  } while (thisDay.getDate() > 1)

  // fill in any trailing blanks
  if (thisDay.getDay() > 0) {
	for (i = 6; i > thisDay.getDay(); i--)
	  html += TD + "&nbsp;" + xTD;
  }
  html += xTR;

  // add a button to allow the user to easily return to today, or close the calendar
  var today = new Date();
  var todayString = "Today is " + dayArrayMed[today.getDay()] + ", " + monthArrayMed[ today.getMonth()] + " " + today.getDate();
  html += TR_todaybutton + TD_todaybutton;
  html += "<button class='dpTodayButton' onClick='refreshDatePicker(\"" + dateFieldName + "\");'>today</button>&nbsp;&nbsp;&nbsp;";
  html += "<button class='dpTodayButton' onClick='updateDateField(\"" + dateFieldName + "\");'>close</button>";
  html += xTD + xTR;

  // and finally, close the table
  html += xTABLE;

  document.getElementById(datePickerDivID).innerHTML = html;
  // add an "iFrame shim" to allow the datepicker to display above selection lists
  adjustiFrame();
}


/**
Convenience function for writing the code for the buttons that bring us back or forward
a month.
*/
function getButtonCode(dateFieldName, dateVal, adjust, label)
{
  var newMonth = (dateVal.getMonth () + adjust) % 12;
  var newYear = dateVal.getFullYear() + parseInt((dateVal.getMonth() + adjust) / 12);
  if (newMonth < 0) {
	newMonth += 12;
	newYear += -1;
  }

  return "<button class='dpButton' onClick='refreshDatePicker(\"" + dateFieldName + "\", " + newYear + ", " + newMonth + ");'>" + label + "</button>";
}


/**
Convert a JavaScript Date object to a string, based on the dateFormat and dateSeparator
variables at the beginning of this script library.
*/
function getDateString(dateVal)
{
  var dayString = "00" + dateVal.getDate();
  var monthString = "00" + (dateVal.getMonth()+1);
  dayString = dayString.substring(dayString.length - 2);
  monthString = monthString.substring(monthString.length - 2);

  switch (dateFormat) {
	case "dmy" :
	  return dayString + dateSeparator + monthString + dateSeparator + dateVal.getFullYear();
	case "ymd" :
	  return dateVal.getFullYear() + dateSeparator + monthString + dateSeparator + dayString;
	case "mdy" :
	default :
	  return monthString + dateSeparator + dayString + dateSeparator + dateVal.getFullYear();
  }
}


/**
Convert a string to a JavaScript Date object.
*/
function getFieldDate(dateString)
{
  var dateVal;
  var dArray;
  var d, m, y;

  try {
	dArray = splitDateString(dateString);
	if (dArray) {
	  switch (dateFormat) {
		case "dmy" :
		  d = parseInt(dArray[0], 10);
		  m = parseInt(dArray[1], 10) - 1;
		  y = parseInt(dArray[2], 10);
		  break;
		case "ymd" :
		  d = parseInt(dArray[2], 10);
		  m = parseInt(dArray[1], 10) - 1;
		  y = parseInt(dArray[0], 10);
		  break;
		case "mdy" :
		default :
		  d = parseInt(dArray[1], 10);
		  m = parseInt(dArray[0], 10) - 1;
		  y = parseInt(dArray[2], 10);
		  break;
	  }
	  dateVal = new Date(y, m, d);
	} else if (dateString) {
	  dateVal = new Date(dateString);
	} else {
	  dateVal = new Date();
	}
  } catch(e) {
	dateVal = new Date();
  }

  return dateVal;
}


/**
Try to split a date string into an array of elements, using common date separators.
If the date is split, an array is returned; otherwise, we just return false.
*/
function splitDateString(dateString)
{
  var dArray;
  if (dateString.indexOf("/") >= 0)
	dArray = dateString.split("/");
  else if (dateString.indexOf(".") >= 0)
	dArray = dateString.split(".");
  else if (dateString.indexOf("-") >= 0)
	dArray = dateString.split("-");
  else if (dateString.indexOf("\\") >= 0)
	dArray = dateString.split("\\");
  else
	dArray = false;

  return dArray;
}

function updateDateField(dateFieldName, dateString)
{
  var targetDateField = document.getElementsByName (dateFieldName).item(0);
  if (dateString && isValidDate(dateFieldName, dateString)) {
      targetDateField.value = dateString;
      userDateFormat(targetDateField);
  } else if (dateString) {
    return;
  }

  var pickerDiv = document.getElementById(datePickerDivID);
  pickerDiv.style.visibility = "hidden";
  pickerDiv.style.display = "none";

  adjustiFrame();
  targetDateField.focus();

  if ((dateString) && (typeof(datePickerClosed) == "function"))
	datePickerClosed(targetDateField);
}


function adjustiFrame(pickerDiv, iFrameDiv)
{
  var is_opera = (navigator.userAgent.toLowerCase().indexOf("opera") != -1);
  if (is_opera)
	return;

  // put a try/catch block around the whole thing, just in case
  try {
	if (!document.getElementById(iFrameDivID)) {
	  var newNode = document.createElement("iFrame");
	  newNode.setAttribute("id", iFrameDivID);
	  newNode.setAttribute("src", "javascript:false;");
	  newNode.setAttribute("scrolling", "no");
	  newNode.setAttribute ("frameborder", "0");
	  document.body.appendChild(newNode);
	}

	if (!pickerDiv)
	  pickerDiv = document.getElementById(datePickerDivID);
	if (!iFrameDiv)
	  iFrameDiv = document.getElementById(iFrameDivID);

	try {
	  iFrameDiv.style.position = "absolute";
	  iFrameDiv.style.width = pickerDiv.offsetWidth;
	  iFrameDiv.style.height = pickerDiv.offsetHeight ;
	  iFrameDiv.style.top = pickerDiv.style.top;
	  iFrameDiv.style.left = pickerDiv.style.left;
	  iFrameDiv.style.zIndex = pickerDiv.style.zIndex - 1;
	  iFrameDiv.style.visibility = pickerDiv.style.visibility ;
	  iFrameDiv.style.display = pickerDiv.style.display;
	} catch(e) {
	}

  } catch (ee) {
  }

}
