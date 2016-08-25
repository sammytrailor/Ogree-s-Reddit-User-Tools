//UPDATE WITH URL (maybe make configurable later on
var server_url = "http://127.0.0.1:8080";

var month_submission_totals = [];
var month_comment_totals = [];
var month_combined_totals = [];
var month_labels = [];
var threshold_data = [];



$(function () {

    //Add our Event Handlers

    $("#btnLookup").click(btnLookup_Click);
    $("#btnForceLookup").click(btnForceLookup_Click);

    // Disable Form submit - stops weird enter button behaviour
    $("#frmSearch").submit(function(){return false;});

    $('#txtUsername').keypress(function(e) {
        if (e.which == 13) {
            btnLookup_Click();
        }
    });

    //Make sure we're not showing an incomplete form.1
    $("#results").hide();



});


// PAGE-LEVEL EVENT HANDLERS ########################################
function btnLookup_Click() {
    //
    //set initial view
    var username = $("#txtUsername").val().trim();

    QueryUser(false, username);
}


function btnForceLookup_Click() {
    var username = $("#txtUsername").val().trim();


    QueryUser(true, username);

}


//  PROCESS USER DATA ##############################################
function QueryUser(force, username) {

    //setup view
    $("#results").hide();
    $("#errorMessage").hide();


    //Check to see if we have a valid username  <-- MOdify if need to include multiple usernames at a later date
    if (username.length <= 0) {
        //Need a username
        DisplayError("Please specify a valid Reddit username");
        return;
    }

    //Show Modal Dialog, we're good to go
    $("#loadingModal").modal({backdrop: "static", keyboard: false})


    var url = server_url;  // "http://reddit.nossquad.com";
    var userData;

    if (force) {
        url = url + "/forceuserdetails/" + username;
    }
    else {
        url = url + "/getuserdetails/" + username;
    }


    //Get User Details and display results
    var jqxhr = $.getJSON(url, function () {
            console.log("successfully retrieved JSON Data for URL: " + url);
        })
        .done(function (data) {
            ProcessUser(data)
        })
        .fail(function (jqXHR, textStatus, errorThrown) {
            console.log("Error thrown: " + textStatus);
            //Handle the error and show something
            DisplayError("Error whilst retrieving data.");
        });


}

function ProcessUser(data) {

    if (data.error > 0) {
        //Raise an error, show the message and get out of here.
        DisplayError("Error whilst retrieving data: " + data.errorMsg);

        return;

    }

    var userData = data.user_data;

    if (data.cached) {
        $("#cache_stats").text("Retrieved from cache. Data retrieved on: " + data.query_time);

    } else {
        $("#cache_stats").text("Retrieved from Reddit on: " + data.query_time );
    }


    DisplayUserDetails(userData);
    DisplayTrophyDetails(userData.trophies);

    DisplayBreakdown(userData.details);
    DisplayComments(userData.eve_content);

    $("#results").show();

    DisplayCharts(userData);

    $("#loadingModal").modal('hide');

}


function DisplayUserDetails(data) {
    //username
    $("#redditUsername").text(data.username)
    $("#redditUserPage").attr("href", "http://reddit.com/u/" + data.username);


    //update the text input with the username (as sometimes the user didn't land on the page this way - will allow them to force
    $("#txtUsername").val(data.username);

    //Creation Dates
    $("#accountCreationDate").text(data.created);
    if (data.creationDateOK) {
        $("#creationDateOK").addClass('label-success');
        $("#creationDateOK").text('OK');
    } else {
        $("#creationDateOK").addClass('label-danger');
        $("#creationDateOK").text('FAIL');
    }


    //Submissions
    $("#totalSubmissions").text(data.totalSubmissions);

    //Comments
    $("#totalComments").text(data.totalComments);

    //Karma
    $("#headerSubmissionKarma").text(data.submissionKarma);
    $("#detailSubmissionKarma").text(data.submissionKarma);

    $("#headerCommentKarma").text(data.commentKarma);
    $("#detailCommentKarma").text(data.commentKarma);

    //First Eve Post
    if (data.hasEveContent) {
        $("#firstEvePost").text(data.firstEvePost);
    } else {
        $("#firstEvePost").text("None found");
    }


    //Redditor Type
    if (data.isGold) {
        $("#IsGold").show();
    }
    else {
        $("#IsGold").hide();
    }

    if (data.isMod) {
        $("#IsMod").show();
    }
    else {
        $("#IsMod").hide();
    }

    if (data.isSuspended) {
        $("#IsSuspended").show();
    }
    else {
        $("#IsSuspended").hide();
    }

    if (data.isEmployee) {
        $("#IsEmployee").show();
    }
    else {
        $("#IsEmployee").hide();
    }

}


function DisplayTrophyDetails(data) {
    $("#trophy_cabinet").empty();
    $.each(data, function (name, trophy_details) {

        desc = (trophy_details.description == null) ? name : name + ": " + trophy_details.description;
        $("#trophy_cabinet").append("<img src='" + trophy_details.icon + "' alt='" + desc + "'>&nbsp;");
    });

}

function DisplayCharts(data) {
    DrawMonthChart();
    // DrawSubredditChart(data.subreddit_totals);
}


function DisplayBreakdown(data) {

    var d = new Date();

    var currentYear = d.getUTCFullYear();
    var currentMonth = d.getUTCMonth() + 1; //0 based - Jan is 0, Dec is 11.

    var month = "";

    var months_limit = 120; // 10 years is a good maximum TODO: Update this and make it configurable?
    var months_displayed = 0;
    var months_processed = 0; //The number of months we've found in our data, (months_displayed - blank or missing months)
    var total_Months_returned = Object.keys(data).length;


    // Reset our charts and forms
    month_submission_totals = [];
    month_comment_totals = [];
    month_combined_totals = [];
    month_labels = [];
    threshold_data = [];


    $("#month_breakdown tbody").empty();



    // While we haven't reached our limit of items to display and there are still months to process
    while (months_displayed < months_limit && months_processed < total_Months_returned) {

        month = currentMonth + "/" + currentYear;
        if (month.length != 7) {
            month = "0" + month;
        }

        month_labels.push(month);
        threshold_data.push(25); // TODO: Make the threshold/required content configurable

        var $tr = "<tr>";

        if (month in data) {
            // We have a month to show
            var details = data[month];

            var subreddit_details = details.subreddits;
            var $ul = "<ul>";

            $.each(subreddit_details, function (subreddit, subreddit_data) {
                if(subreddit_data != undefined) {
                    $ul += "<li>" + subreddit + " " + subreddit_data.totalSubmissions + " / " + subreddit_data.totalComments + "</li>";


                }
            });


            $ul += "</ul>";

            $tr += "<td>" + month + "</td>";
            $tr += "<td><b>" + details.totalSubmissions + "</b>(" + details.totalSubmissionKarma + ")</td>";
            $tr += "<td><b>" + details.totalComments + "</b>(" + details.totalCommentKarma + ")</td>";
            $tr += "<td>" + $ul + "</td>";


            month_comment_totals.push(details.totalComments);
            month_submission_totals.push(details.totalSubmissions);
            month_combined_totals.push(details.totalComments + details.totalSubmissions);


            months_processed += 1; //We've dealt with a month from our results
        } else {
            //show a blank month


            $tr += "<td>" + month + "</td>";
            $tr += "<td></td>";
            $tr += "<td></td>";
            $tr += "<td></td>";

            //Ensure we have a value for this month in our grapah
            month_comment_totals.push(0);
            month_submission_totals.push(0);
            month_combined_totals.push(0);
        }
        $tr += "</tr>";
        $("#month_breakdown tbody").append($tr);


        months_displayed += 1;
        currentMonth -= 1;
        // Previous year!
        if (currentMonth <= 0) {
            currentYear -= 1;
            currentMonth = 12;
        }

    }


}

function DisplayComments(data) {

    //Clean up from a potential previous run
    $('#commentBreakdown').empty();

    $.each(data, function (id, details) {

        var $eveItem = "<div class='eveItem'>"

        if (details.is_submission) {

            $eveItem += "<div>";
            $eveItem += "<a href='" + details.url + "'>" + details.link_title + "</a> by  <a href='http://reddit.com/user/" + details.link_author + "'>" + details.link_author + "</a>";
            $eveItem += " on " + details.created + "</div>"
            $eveItem += "<div>" + details.body + "</div>";


        } else {

            $eveItem += "<div>";
            $eveItem += "<a href='" + details.url + "'>" + details.link_title + "</a> by  <a href='http://reddit.com/user/" + details.link_author + "'>" + details.link_author + "</a>";
            $eveItem += " on " + details.created + "</div>"
            $eveItem += "<div>" + details.body + "</div>";
        }

        $eveItem += "</div>";
        $('#commentBreakdown').append($eveItem);

        $(".eveItem:even").css('background-color','#FFFFFF');
        $(".eveItem:odd").css('background-color','#F9F9F9');

    });

}

function DisplayError(errorMsg) {
    $("#results").hide();

    $("#errorMessage").html(errorMsg);

    $("#loadingModal").modal('hide');
    $("#errorMessage").show(200);

}


function DrawSubredditChart(subreddit_data) {
    //Breakdown per subreddit

    var maxSubredditsShown = 10;
    //Sort our data appropriately
    var submissionTotals = SortJSONByParam(subreddit_data,'totalThings',false);
    var karmaTotals = SortJSONByParam(subreddit_data,'totalKarma',false);



    var submissionLabels = [];
    var submissionValues = [];

    var submissionSeries = [];
    var karmaSeries = [];

    var karmaLabels = [];
    var karmaValues = [];

    var subredditsProcessed = 0;
    var otherTotal = 0;
    $.each(subreddit_data,function(subreddit,totals) {

        console.log ("beep  beep");

        if (subredditsProcessed >= maxSubredditsShown) {
            //combine any excessive values into an "other"
            otherTotal += totals.totalThings;

        }
        else {

            submissionSeries.push(subreddit,totals);
        }
        subredditsProcessed += 1;
    });

    submissionLabels.push("Other");
    submissionValues.push(otherTotal);

   // console.log(submissionLabels);

    subredditsProcessed = 0;
    otherTotal = 0;
    $.each(subreddit_data,function(subreddit,totals) {

        if (subredditsProcessed >= maxSubredditsShown){
            karmaLabels.push(subreddit);
            karmaValues.push(totals.totalKarma);

            subredditsProcessed += 1;

        }

    });

    karmaLabels.push("Other");
    karmaValues.push(otherTotal);




     $('#submissionBreakdownChart').highcharts({
         chart: {
            plotBackgroundColor: null,
            plotBorderWidth: null,
            plotShadow: false,
            type: 'pie'
        },
        title: {
            text: 'Subreddit breakdown: Links + Comments'
        },
         credits: {
            enabled: false
        },plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: true,
                    format: '<b>{point.name}</b>: {point.y} %',
                    style: {
                        color: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
                    },
                    connectorColor: 'silver'
                }
            }
        },series: [{
             name: 'Subreddits',
             data: submissionValues,
             dataLabels: submissionLabels
        }]
     });

    $('#karmaBreakdownChart').highcharts({
         chart: {
            plotBackgroundColor: null,
            plotBorderWidth: null,
            plotShadow: false,
            type: 'pie'
        },
        title: {
            text: 'Total Karma Breakdown'
        },
         credits: {
            enabled: false
        },plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: true,
                    format: '<b>{point.name}</b>: {point.y} %',
                    style: {
                        color: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
                    },
                    connectorColor: 'silver'
                }
            }
        },series: [{
             name: 'Subreddits',
             data: karmaValues,
             dataLabels: karmaLabels
        }]
     });
}


function DrawMonthChart(data) {

    $('#monthChart').highcharts({
        chart: {
            type: 'column'
        },
        title: {
            text: 'Monthly Content'
        },
        subtitle: {
            text: ''
        },
        credits: {
            enabled: false
        },
        xAxis: {
            categories: month_labels,
            crosshair: true
        },
        yAxis: {
            min: 0,
            title: {
                text: '# Submissions'
            }
        },
        tooltip: {
            headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
            pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
            '<td style="padding:0"><b>{point.y}</b></td></tr>',
            footerFormat: '</table>',
            shared: true,
            useHTML: true
        },
        plotOptions: {
            column: {
                pointPadding: 0.2,
                borderWidth: 0
            },
            series: {
                marker: {
                    enabled: false
                }
            }
        },
        series: [{
            name: 'Total',
            data: month_combined_totals

        }, {
            name: 'Comments',
            data: month_comment_totals

        }, {
            name: 'Submissions',
            data: month_submission_totals

        }, {
            type: 'line',
            name: 'limit',
            data: threshold_data

        }]

    });

}

function SortJSONByParam(unsorted,prop,asc) {
    var sorted_data = $(unsorted).sort(function(a,b) {
        if (asc) return (a[prop] > b[prop]) ? 1 : ((a[prop] < b[prop]) ? -1 : 0);
        else return (b[prop] > a[prop]) ? 1 : ((b[prop] < a[prop]) ? -1 : 0);
    });
    return sorted_data;

}