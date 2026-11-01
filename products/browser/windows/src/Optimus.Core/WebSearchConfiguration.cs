namespace Optimus.Core;

public enum WebProvider { None = 0, Mwmbl = 1, Searx = 2 }

/// <summary>Effective Web configuration; an inactive remembered server never becomes active implicitly.</summary>
public readonly record struct WebSearchConfiguration
{
    public WebProvider Provider { get; }
    public string? Endpoint { get; }

    public WebSearchConfiguration(WebProvider provider, string? endpoint = null)
    {
        if (!Enum.IsDefined(provider)) throw new ArgumentException("Fuente Web no válida.");
        if (provider == WebProvider.Searx && (endpoint is null || !OptimusSearchService.IsValidEndpoint(endpoint)))
            throw new ArgumentException("Elige un servidor SearXNG válido.");
        Provider = provider;
        Endpoint = provider == WebProvider.Searx ? endpoint : null;
    }

    public static WebSearchConfiguration FromSettings(BrowserSettings settings)
    {
        ArgumentNullException.ThrowIfNull(settings);
        return new(settings.WebProvider ?? (settings.SearxEndpoint is null ? WebProvider.None : WebProvider.Searx), settings.SearxEndpoint);
    }
}
