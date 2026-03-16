/////////////////////////////////////////////////////////////////////////////////////////////
//Header
//
//Company:            Trimble Inc
/////////////////////////////////////////////////////////////////////////////////////////////
using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Trimble.Identity;


namespace ExtensionDataSignalR_SampleCode
{
	public enum AuthorityEnvironment
	{
		Production,
		Staging,
	}

	public class TrimbleIdentityService
	{
		public AuthenticationResult CurrentSession { get; private set; }

		private string Scopes => $"openid {_applicationName}";

		private readonly string _applicationName;
		private readonly AuthenticationContext _authenticationContext;
		private CancellationTokenSource _cancellationTokenSource;

		public TrimbleIdentityService(string applicationName, string consumerKey, string consumerSecret, AuthorityEnvironment authorityEnvironment, params string[] redirectUrls)
		{
			try
			{
				_applicationName = applicationName;
				var redirectUris = redirectUrls.Select(x => new Uri(x, UriKind.Absolute));
				var redirectUri = GetOpenRedirectUri(redirectUris);

				var clientCredential = new ClientCredential(consumerKey, consumerSecret, _applicationName)
				{
					// registered URL in API Cloud must have trailing backslash
					RedirectUri = redirectUri
				};

				_authenticationContext = new AuthenticationContext(clientCredential, new TokenCache())
				{
					AuthorityUri = new Uri(GetAuthorityUri(authorityEnvironment), UriKind.Absolute)
				};
			}
			catch (Exception exp)
			{
				MessageBox.Show(exp.Message);
			}
		}

		public async Task<AuthenticationResult> LoginAsync()
		{
			ResetCancellationToken();

			try
			{
				CurrentSession = await _authenticationContext.AcquireTokenAsync(
					new InteractiveAuthenticationRequest
					{
						Scope = Scopes
					}, _cancellationTokenSource.Token
					).ConfigureAwait(false);

				return CurrentSession;
			}
			catch (TaskCanceledException)
			{
				return null;
			}
			catch (Exception exp)
			{
				MessageBox.Show(exp.Message);
				return null;
			}
		}

		public void Logout()
		{
			if (CurrentSession == null)
			{
				return;
			}

			_authenticationContext.RevokeAsync(CurrentSession).GetAwaiter().GetResult();

			ResetCancellationToken();
			_authenticationContext.LogoutAsync(CurrentSession, _cancellationTokenSource.Token).GetAwaiter().GetResult();

			CurrentSession = null;
		}

		public AuthenticationResult Refresh()
		{
			try
			{
				if (CurrentSession == null)
				{
					return null;
				}

				CurrentSession = _authenticationContext.AcquireTokenByRefreshTokenAsync(CurrentSession).GetAwaiter().GetResult();
				//			var mySession = CurrentSession;
				return CurrentSession;
			}
			catch (Exception exp)
			{
				MessageBox.Show(exp.Message);
				return null;
			}
		}

		public async Task RevokeAsync()
		{
			if (CurrentSession == null)
			{
				return;
			}

			await _authenticationContext.RevokeAsync(CurrentSession);
			CurrentSession = null;
		}

		private static string GetAuthorityUri(AuthorityEnvironment authorityEnvironment)
		{
			if (authorityEnvironment == AuthorityEnvironment.Production)
			{
				return AuthorityUris.ProductionUri;
			}
			else
			{
				return AuthorityUris.StagingUri;
			}
		}

		private static Uri GetOpenRedirectUri(IEnumerable<Uri> redirectUris)
		{
			using (var tcpClient = new TcpClient())
			{
				foreach (var redirectUri in redirectUris)
				{
					try
					{
						tcpClient.BeginConnect(redirectUri.Host, redirectUri.Port, null, null);
						return redirectUri;
					}
					catch
					{
						// move on
					}
				}
			}

			throw new Exception("None of the supplied redirect urls are using an open port.");
		}

		private void ResetCancellationToken()
		{
			try
			{
				if (_cancellationTokenSource != null)
				{
					_cancellationTokenSource.Cancel();
					_cancellationTokenSource.Token.WaitHandle.WaitOne();
					_cancellationTokenSource.Dispose();
				}

				_cancellationTokenSource = new CancellationTokenSource();
			}
			catch (Exception exp)
			{
				MessageBox.Show(exp.Message);
			}
		}
	}
}
