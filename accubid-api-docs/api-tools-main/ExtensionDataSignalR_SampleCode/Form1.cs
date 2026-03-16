/////////////////////////////////////////////////////////////////////////////////////////////
//Header
//
//Company:            Trimble Inc
/////////////////////////////////////////////////////////////////////////////////////////////
using System;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.AspNetCore.SignalR.Client;
using Microsoft.Extensions.Logging;
using Trimble.Identity;

namespace ExtensionDataSignalR_SampleCode
{
    public partial class Form1 : Form
    {

        //In order to call our APIs, an access token must be included as an Authorization Bearer token. This access token is
        //required for authentication.
        private string _accessToken;

        //A connection to our signalR hub needs to be established before notifications can be received. The HubConnectionBuilder
        //creates this connection
        private HubConnection _connection;

        //The signalRHubURL is the url to connect to the signalR hub. This url contains two parts. The first part (serverURL) is the
        //url to the API that is being called. The second part is the name of the signalR hub to establish connection with.
        static string serverURL = "https://cloud.api.trimble.com/anywhere/estimate/v1";
        string signalRHubURL = $"{serverURL}/notification";

        //For the purpose of testing the connection to signalR hub, there is also a testApiURL.
        //This api will send a test message via SignalR to test the SignalR connection. ( see buttonCallTestAPI_Click below)
        string testApiURL = $"{serverURL}/notificationtest";

        //The following values are needed in order to get an access token. These values are from the Trimble Cloud application registration.
        string consumerSecret = <PLEASE INSERT CONSUMER SECRET HERE>;
        string consumerKey = <PLEASE INSERT CONSUMER KEY HERE>;
        string applicationName = <PLEASE INSERT APPLICATION NAME HERE>;

        public Form1()
        {
            InitializeComponent();
            buttonConnect.Enabled = true;
            buttonCallAPI.Enabled = false;
            buttonGetExtensionData.Enabled = false;
        }

        //HOW TO CONNECT TO SIGNALR HUB
        //-----------------------------

        private void buttonConnect_Click(object sender, EventArgs e)
        {
            //Create a new instance of the HubConnection Class by passing the signalRHubURL as the url parameter and specifying
            //the access token as option. Although the access token is specified as an option, in this case it is necessary to have
            //the access token specified in order to be able to access our APIs through the Trimble Cloud services.
            //Finally, the Build() method builds the Hub connection with the configured options.
            _connection = new HubConnectionBuilder()
                 .WithUrl(signalRHubURL, options =>
                 {
                     options.AccessTokenProvider = () => Task.FromResult(_accessToken);
                 })
                .ConfigureLogging(logging =>
                {
                    logging.AddDebug();
                    logging.AddFilter("Microsoft.AspNetCore.SignalR", LogLevel.Debug);
                }).Build();

            //This handler listens for a method called “notificationMessage” and receives the message sent from the signalR hub.
            //This message will contain a URL to download the file
            _connection.On<string>("notificationMessage", (message) =>
            {
                var newMessage = $"{message}";
                messageBox.AppendText("\r\n" + newMessage.ToString());
            });

            // StartAsync() starts a connection to the server.
            _connection.StartAsync().ConfigureAwait(false);

            messageBox.AppendText("\nConnected");

            buttonConnect.Enabled = false;
            buttonCallAPI.Enabled = true;
            buttonGetExtensionData.Enabled = true;
        }

        //When a client connects to a signalR hub, the client is automatically assigned a connectionID.
        //Checking if this connectionID exists is one way to test if the client has successfully connected.
        private void buttonCallTestAPI_Click(object sender, EventArgs e)
        {
            if (string.IsNullOrEmpty(_connection.ConnectionId))
            {
                messageBox.AppendText("\r\nNo SignalR connection");
                buttonConnect.Enabled = true;
                buttonCallAPI.Enabled = false;
                buttonGetExtensionData.Enabled = false;
                return;
            }

            HttpClient client = new HttpClient();

            var request = new HttpRequestMessage
            {
                Method = HttpMethod.Get,
                RequestUri = new Uri($"{testApiURL}/{_connection.ConnectionId}"),
            };

            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _accessToken);

            client.SendAsync(request).ConfigureAwait(false);
        }

        private void buttonGetExtensionData_Click(object sender, EventArgs e)
        {
            if (String.IsNullOrEmpty(DatabaseID_textBox.Text))
            {
                System.Windows.Forms.MessageBox.Show("Please provide Database Token");
            }

            if (String.IsNullOrEmpty(EstimateID_textBox.Text))
            {
                System.Windows.Forms.MessageBox.Show("Please provide Encypted EstimateID");
            }

            //Create a new instance of a class for sending Http request and receiving Http responses
            HttpClient client = new HttpClient();

            string databaseID = DatabaseID_textBox.Text;
            string estimateID = EstimateID_textBox.Text;

            //Initializes a new instance of the HttpRequestMessage class with a Get method and a RequestUri. The RequestUri contains
            //the encrypted database and estimate ID.
            var request = new HttpRequestMessage
            {
                Method = HttpMethod.Get,
                RequestUri = new Uri($"{serverURL}/extensionitemdetailsfilesignalr/{databaseID}/{estimateID}/{_connection.ConnectionId}"),
            };

            //The access token also needs to be added as a bearer to the header of the request in order access trimble cloud.
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _accessToken);

            // A new instance of the HttpRequestMessage class to receive the response of the request that was sent.
            HttpResponseMessage response = client.SendAsync(request).GetAwaiter().GetResult();

            //Gets the content of the HTTP message.
            string reply = response.Content.ReadAsStringAsync().GetAwaiter().GetResult().ToString();

            //If status code of response is not 200 OK, the status code is displayed
            if (response.StatusCode != HttpStatusCode.OK)
            {
                messageBox.AppendText("\r\n" + response.StatusCode.ToString());
            }

            messageBox.AppendText("\r\n" + response.ToString());

            //Displays content of HTTP message. The content has the following format
            /*
             * bool Success - True/False
             * string DataType
             * string Data - it will contain either data (Blob URL in case of Extension) if Success was True or an empty string if Success was False.
             * string AdditionalInfo - we will not use it for now but may keep it for future needs. It should be "null" for now.
             * string Message -Will contain an error message if Success was False or and empty string if Success was True.
            */
            messageBox.AppendText("\r\n" + reply.ToString());
        }

        private void buttonClear_Click(object sender, EventArgs e)
        {
            messageBox.Clear();
        }

        private void buttonLoginProd_Click(object sender, EventArgs e)
        {
            if (String.IsNullOrEmpty(applicationName))
            {
                System.Windows.Forms.MessageBox.Show("The value of the application name must be assigned in the sample code");
            }

            if (String.IsNullOrEmpty(consumerKey))
            {
                System.Windows.Forms.MessageBox.Show("The value of the consumer key must be assigned in the sample code");
            }

            if (String.IsNullOrEmpty(consumerSecret))
            {
                System.Windows.Forms.MessageBox.Show("The value of the consumer secret must be assigned in the sample code");
            }

            Task<AuthenticationResult> task = CloudLoginProduction();

            task.ContinueWith(tasks => Invoke(new OnLoginCompleteMessageCallback(OnLoginCompleteMessage), new object[] { task.Result, null }));
        }

        //The TrimbleIdentityService class is used for the creation of the access token. The consumerKey and consumerSecret for the
        //respective application name are found in Trmble Cloud.
        private async Task<AuthenticationResult> CloudLoginProduction()
        {
            TrimbleIdentityService identityService = new TrimbleIdentityService(applicationName, consumerKey, consumerSecret, AuthorityEnvironment.Production, "http://127.0.0.1/");

            return await identityService.LoginAsync();
        }

        delegate void OnLoginCompleteMessageCallback(object obj, EventArgs e);

        //This is a callback that gets called after the user logs in.
        public void OnLoginCompleteMessage(object obj, EventArgs e)
        {
            if ((obj == null) ||
                (!(obj is AuthenticationResult)))
            {
                return;
            }

            AuthenticationResult authenticationResult = (AuthenticationResult)obj;

            _accessToken = authenticationResult.AccessToken;
        }
    }
}
