namespace Optimus.Search;

public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        try
        {
            var import = args.Length > 0 && args[0] == "index";
            var allowed = import ? new[] { "--input", "--output" } : new[] { "--port", "--index-file", "--token-file", "--searx-url", "--owner-stdin", "--web-provider", "--owner-identity-stdout" };
            var values = new Dictionary<string, string>(StringComparer.Ordinal);
            for (var i = import ? 1 : 0; i < args.Length; i += 2)
            {
                if (i + 1 >= args.Length || !allowed.Contains(args[i], StringComparer.Ordinal) || string.IsNullOrWhiteSpace(args[i + 1]) || !values.TryAdd(args[i], args[i + 1])) throw new ArgumentException();
            }
            if (import)
            {
                if (!values.TryGetValue("--input", out var input) || !values.TryGetValue("--output", out var output)) throw new ArgumentException();
                await CatalogStore.ImportAsync(input, output);
                Console.WriteLine("Catalog imported.");
                return 0;
            }
            var ownerStdin = values.TryGetValue("--owner-stdin", out var ownerValue);
            if (ownerStdin && (ownerValue != "true" || !Console.IsInputRedirected)) throw new ArgumentException();
            var ownerIdentity = values.TryGetValue("--owner-identity-stdout", out var identityValue);
            if (ownerIdentity && (identityValue != "true" || !ownerStdin || !Console.IsOutputRedirected)) throw new ArgumentException();
            var port = 17831;
            if (values.TryGetValue("--port", out var portValue) && (!int.TryParse(portValue, System.Globalization.NumberStyles.None, System.Globalization.CultureInfo.InvariantCulture, out port) || port is < 0 or > 65535)) throw new ArgumentException();
            if (values.TryGetValue("--web-provider", out var selected) && (selected != "mwmbl" || values.ContainsKey("--searx-url"))) throw new ArgumentException();
            using IWebSearchProvider? provider = selected == "mwmbl" ? new MwmblSearchProvider() : values.TryGetValue("--searx-url", out var endpoint) ? new SearxSearchProvider(endpoint) : null;
            var explicitIndex = values.TryGetValue("--index-file", out var indexPath);
            indexPath ??= Path.Combine(AppContext.BaseDirectory, "index.json");
            var documents = explicitIndex || File.Exists(indexPath) ? await CatalogStore.LoadAsync(indexPath) : [];
            var token = await TokenStore.LoadOrCreateAsync(values.GetValueOrDefault("--token-file") ?? TokenStore.DefaultPath);
            await using var server = await SearchServer.StartAsync(new ServerOptions(port, token), new LocalSearchIndex(documents), provider);
            // This public key belongs to the listener that has actually bound, and is
            // delivered only through the launcher-created private child pipe.
            Console.WriteLine(ownerIdentity ? $"OptimusSearch owner/1|{new Uri(server.Address).Port}|{server.TlsSpkiSha256}" : "OptimusSearch ready.");
            var shutdown = server.WaitForShutdownAsync();
            if (ownerStdin)
            {
                // Console.In can block even for ReadAsync. Keep that read off the
                // calling path so an independent normal shutdown can still win.
                var completed = await Task.WhenAny(shutdown, Task.Run(WaitForOwnerEofAsync));
                await completed;
            }
            else await shutdown;
            return 0;
        }
        catch (Exception)
        {
            Console.Error.WriteLine("Unable to start search or import catalog. Check local configuration.");
            return 2;
        }
    }

    private static async Task WaitForOwnerEofAsync()
    {
        var buffer = new char[256];
        while (await Console.In.ReadAsync(buffer.AsMemory()) != 0) { }
    }
}
