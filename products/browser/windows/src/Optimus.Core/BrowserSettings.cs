namespace Optimus.Core;
public record BrowserSettings
{
 public SearchProvider SearchProvider { get; init; } = SearchProvider.Optimus;
 public List<PrivacyRule> PrivacyRules { get; init; } = PrivacyPolicy.Seeds();
 public string? SearxEndpoint { get; init; }
 public double TextScale { get; init; } = 1;
 public ThemePreference Theme { get; init; } = ThemePreference.Dark;
 public bool EasyMode { get; init; }
 public bool HighContrast { get; init; }
 public bool RestoreSession { get; init; }
 public List<string> SessionUrls { get; init; } = [];
 public List<Bookmark> Bookmarks { get; init; } = [];
}
