namespace Optimus.Search;

public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        try
        {
            var import = args.Length > 0 && args[0] == "index";
            var allowed = import ? new[] { "--input", "--output" } : new[] { "--port", "--index-file", "--token-file", "--searx-url" };
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
            var port = 17831;
            if (values.TryGetValue("--port", out var portValue) && (!int.TryParse(portValue, System.Globalization.NumberStyles.None, System.Globalization.CultureInfo.InvariantCulture, out port) || port is < 0 or > 65535)) throw new ArgumentException();
            using var provider = values.TryGetValue("--searx-url", out var endpoint) ? new SearxSearchProvider(endpoint) : null;
            var explicitIndex = values.TryGetValue("--index-file", out var indexPath);
            indexPath ??= Path.Combine(AppContext.BaseDirectory, "index.json");
            var documents = explicitIndex || File.Exists(indexPath) ? await CatalogStore.LoadAsync(indexPath) : [];
            var token = await TokenStore.LoadOrCreateAsync(values.GetValueOrDefault("--token-file") ?? TokenStore.DefaultPath);
            await using var server = await SearchServer.StartAsync(new ServerOptions(port, token), new LocalSearchIndex(documents), provider);
            Console.WriteLine("OptimusSearch ready.");
            await server.WaitForShutdownAsync();
            return 0;
        }
        catch (Exception ex) when (ex is ArgumentException or IOException or InvalidDataException or UnauthorizedAccessException or InvalidOperationException or System.Net.Sockets.SocketException)
        {
            Console.Error.WriteLine("Unable to start search or import catalog. Check local configuration.");
            return 2;
        }
    }
}
