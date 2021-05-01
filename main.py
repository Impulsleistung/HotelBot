# Import section
from flask import Flask, request, render_template, make_response, jsonify
import pandas as pd
from tabulate import tabulate
from random import randrange
import datetime
import dateutil.parser
# Import section

# Startup routine
print("### start up ###")
app = Flask(__name__)

# Init Process: System Variables #
intentName = "No intent"
traceResponse = "Response from Flask. Why do you see me?"
# Init Process: System Variables #

# Init Process: Reservation Values #
# Explitcit use of global variables for architectural rapid prototyping
setConfirm = False
reservationID = 666
startDate = datetime.datetime.now()
reservationDays = 0
customerName = "Ninalina"
startDateShortStr = startDate.strftime("%A, %d of %B")
df_init = pd.DataFrame(
    {
        'Start Date Long': startDate,
        'Start Date': startDateShortStr,
        'Days': reservationDays,
        'Customer': customerName
    },
    index=[reservationID])
getReservationID = 0
getDeletePerson = "Not a name"

# Display the initial pandas customer table: df_init
print(tabulate(
    df_init,
    headers="keys",
    tablefmt="psql",
))
# Init Process: Reservation Values #

# Start App, open ports
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)


# HTML entry point. This is needed to indicate that the server is running
@app.route("/")
def index():
    # Static Homepage, Indicator
    return render_template("index.html")


# Dialogflow-API
@app.route("/webhook", methods=["GET", "POST"])
def respond():
    # Write all requests from Dialogflow to CSV for debugging
    # Convert the JSON from Dialogflow to a flat-pandas dataframe
    flattenResult()
    # Call main routine for intent specific handling
    intentDetector()
    # The following JSON string is transmitted back to Dialogflow
    return make_response(jsonify(results()))


# Finalize the response string from flask to Dialogflow
def results():
    return {"fulfillmentText": traceResponse}


# Converting from JSON to Pandas table format
def flattenResult():
    # Table is global for debugging
    global pd_norm

    print("### flatten the json ###")
    # Get the request from Dialogflow and translate to table format
    pd_norm = pd.json_normalize(request.json)

    # Show the column names for debugging reasons
    print(pd_norm.columns)

    # Append the normalized result from Dialogflow to a CSV table for trace/debugging
    pd_norm.to_csv("fromDialogflow_NORM.csv", mode="a", header=True)

    return True


# The response from Dialogflow is based on a defined intent. The intent is detected here
def intentDetector():
    # The content of the received intent is
    # 1. Normalized into pd_norm
    # 2. Stored in global variables for better debugging
    global setConfirm
    global reservationID
    global startDate
    global reservationDays
    global customerName
    global df_init
    global getReservationID
    global getDeletePerson

    # The name of the intent is extracted from the corresponding column
    intentName = pd_norm["queryResult.intent.displayName"].values[0]
    print("### Detected intent is " + intentName)

    # When receiving the intent: CustomerHelp, there's nothing to do for the flask backend. It will be handled by Dialogflow internally. No database operation needed
    if intentName == "CustomerHelp":
        # Forward the suggested intent from Dialogflow back
        passOnly(intentName)

    # When receiving the intent: ReservationCancel, the corresponding line in the database will be removed/dropped.
    if intentName == "ReservationCancel":
        getDropID = int(pd_norm["queryResult.parameters.number"].values[0])
        df_init.drop(getDropID, inplace=True)
        readPandas()

        passOnly(intentName)

    # When receiving the intent: ReservationGet, extract the reservation number queryResult.parameters.number and send back the underlying reservation
    if intentName == "ReservationGet":
        # Extract the reservation number
        getReservationID = int(
            pd_norm["queryResult.parameters.number"].values[0])

        # Call routine for reservation retrievement
        passGetReservationID(intentName)

    # When receiving the intent: ReservationBook, extract the day for check-in and the number of days for the customer stay
    if intentName == "ReservationBook":
        setConfirm = False
        reservationID = randrange(999)
        startDate = pd_norm["queryResult.parameters.date-time"].values[0]
        startDate = startDate[0]
        # The date can come in the form of a list or a dictionary. When Dialogflow sends a dict, this workaround is used
        if isinstance(startDate, dict):
            startDate = startDate.get('date_time')

        # Check the raw date format
        print("Date Debug: " + startDate)
        startDate = dateutil.parser.parse(startDate)
        reservationDays = int(
            pd_norm["queryResult.parameters.number"].values[0])

        # Check the translated date format
        print("The Start is " + startDate.strftime("%m/%d/%Y") + " and days " +
              str(reservationDays))
        passOnly(intentName)

    # When receiving the intent: "ReservationBook - yes", no database operation is made. A flag gets set when the customer confirms the reservation
    if intentName == "ReservationBook - yes":
        passOnly(intentName)
        setConfirm = True

    # When receiving the intent: "ReservationBook - cancel", no database operation is made. The customer has decided to not confirm the reservation
    if intentName == "ReservationBook - cancel":
        setConfirm = False
        passOnly(intentName)

    # When receiving the intent: CustomerDelete -> (1.) The name of the customer is retrieved
    if intentName == "CustomerDelete":
        getDeletePerson = pd_norm["queryResult.parameters.person.name"].values[
            0]
        print("### Deletion of customerbase: " + getDeletePerson)

        passOnly(intentName)

    # When receiving the intent: "CustomerDelete - no", the customer stays in the pandas database. No further action
    if intentName == "CustomerDelete - no":
        passOnly(intentName)

    # When receiving the intent: "CustomerDelete - yes", all rows which contain this name will be dropped
    if intentName == "CustomerDelete - yes":
        # The .drop won't work with a non index call. Instead subsetting is used
        df_init = df_init[df_init.Customer != getDeletePerson]
        # Check if the customer is really deleted
        readPandas()
        passOnly(intentName)

    # Dialogflow default intent
    if intentName == "Default Fallback Intent":
        passOnly(intentName)

    # Dialogflow default intent
    if intentName == "Default Welcome Intent":
        passOnly(intentName)

    # When receiving the intent: "ReservationBook - yes - custom", the customer has confirmed the reservation and gave his/her name. In this case, the entry is made to the database
    if intentName == "ReservationBook - yes - custom":
        passReservationID(intentName)
        # Retrieve the customer name
        customerName = pd_norm["queryResult.parameters.person.name"].values[0]
        # Add an entry with the booking to the database
        writePandas()

    return True


# Helper-Function: The intent fulfillment message is passed through
def passOnly(intentName):
    global traceResponse
    print("handling " + intentName)
    traceResponse = pd_norm["queryResult.fulfillmentText"].values[0]


# Helper-Function: The backend-generated reservation ID is attached to the fulfillment
def passReservationID(intentName):
    global traceResponse
    print("handling " + intentName)
    # Add the reservation ID, so the customer can always ask for the status
    traceResponse = pd_norm["queryResult.fulfillmentText"].values[
        0] + ": " + str(reservationID)


# Helper-Function: The reservation ID is looked up in the pandas database. The customer recieves the information for his/hers reservation
def passGetReservationID(intentName):
    global traceResponse
    # The reservation is for 'Customer' and starting from 'Start Date' for 'Days' days
    print("handling " + intentName)
    res = 'The reservation is for ' + df_init.loc[
        getReservationID, 'Customer'] + ' and starting from ' + df_init.loc[
            getReservationID, 'Start Date'] + ' for ' + str(
                df_init.loc[getReservationID, 'Days']) + ' days'
    traceResponse = pd_norm["queryResult.fulfillmentText"].values[0] + res


# Helper-Function: Add the booking information as a row to the database (df_init)
def writePandas():
    global setConfirm
    global reservationID
    global startDate
    global reservationDays
    global customerName
    global df_init
    print("Routine writePandas")
    startDateShortStr = startDate.strftime("%A, %d of %B")
    df = pd.DataFrame(
        {
            'Start Date Long': startDate,
            'Start Date': startDateShortStr,
            'Days': reservationDays,
            'Customer': customerName
        },
        index=[reservationID])
    df_init = df_init.append(df)

    readPandas()

    return True


# Helper-Function: Print the complete database with all entries to the console in a human readable format
def readPandas():
    print(tabulate(
        df_init,
        headers="keys",
        tablefmt="psql",
    ))
    # Print out the structure of the database
    print("### Structural integrity")
    print(df_init.dtypes)
    return True
