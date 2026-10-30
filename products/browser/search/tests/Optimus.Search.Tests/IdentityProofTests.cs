using System.Net;
using System.Security.Cryptography;
using System.Text;
using Optimus.Search;

static class IdentityProofTests
{
    public static void Register(Action<string, Func<Task>> test)
    {
        // Catches omitting the challenge proof, using raw token bytes as key, or binding the configured zero/Host port.
        test("health challenge proves profile token possession bound to actual listener port", async () =>
        {
            const string token = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
            const string nonce = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789";
            await using var server = await SearchServer.StartAsync(new(0, token), new LocalSearchIndex([]));
            using var client = new HttpClient(TestTls.Handler(() => token)) { BaseAddress = new(server.Address) };
            using var request = new HttpRequestMessage(HttpMethod.Get, "/health");
            request.Headers.Add("X-Optimus-Nonce", nonce);
            using var response = await client.SendAsync(request);
            Require(response.StatusCode == HttpStatusCode.OK, "Challenge must remain public health");
            Require(response.Headers.TryGetValues("X-Optimus-Proof", out var proofs), "Missing possession proof");
            var actual = proofs!.Single();
            var message = $"OptimusSearch/v1|127.0.0.1:{client.BaseAddress.Port}|{nonce}";
            var expected = Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.ASCII.GetBytes(token), Encoding.ASCII.GetBytes(message)));
            Require(actual == expected, "Proof must use exact ASCII key/message and actual port");
            Require(await response.Content.ReadAsStringAsync() == "{\"name\":\"OptimusSearch\",\"version\":1}", "Health metadata changed");
            using var publicHealth = await client.GetAsync("/health");
            Require(publicHealth.StatusCode == HttpStatusCode.OK && !publicHealth.Headers.Contains("X-Optimus-Proof"), "Nonceless health must stay metadata only");
            using var forgedHost = new HttpRequestMessage(HttpMethod.Get, "/health");
            forgedHost.Headers.Add("X-Optimus-Nonce", nonce); forgedHost.Headers.Host = "127.0.0.1:1";
            using var forbidden = await client.SendAsync(forgedHost);
            Require(forbidden.StatusCode == HttpStatusCode.Forbidden && !forbidden.Headers.Contains("X-Optimus-Proof"), "Arbitrary Host cannot select a proof port");
        });
        // Catches signing malformed or multiple challenges and reflecting them or corpus state in error bodies.
        test("health rejects malformed or multiple nonces with generic 400 and no proof", async () =>
        {
            await using var server = await SearchServer.StartAsync(new(0, new string('a', 64)), new LocalSearchIndex([]));
            using var client = new HttpClient(TestTls.Handler()) { BaseAddress = new(server.Address) };
            foreach (var values in new[] { new[] { "" }, new[] { "sensitive-invalid-nonce" }, new[] { new string('g', 64) }, new[] { new string('a', 63) }, new[] { new string('a', 65) }, new[] { new string('a', 64), new string('b', 64) } })
            {
                using var request = new HttpRequestMessage(HttpMethod.Get, "/health");
                request.Headers.TryAddWithoutValidation("X-Optimus-Nonce", values);
                using var response = await client.SendAsync(request);
                Require(response.StatusCode == HttpStatusCode.BadRequest, "Malformed nonce must be rejected");
                Require(!response.Headers.Contains("X-Optimus-Proof"), "Invalid challenge must not receive proof");
                Require(await response.Content.ReadAsStringAsync() == "{\"error\":\"invalid-request\",\"message\":\"Invalid request.\"}", "Nonce error must be generic and metadata free");
            }
        });
    }
    private static void Require(bool value, string message) { if (!value) throw new Exception(message); }
}
