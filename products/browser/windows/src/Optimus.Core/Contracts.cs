namespace Optimus.Core;
public enum SearchProvider { DuckDuckGo=0, Google=1, Optimus=2 }
public record NavigationResult(Uri? Uri, bool IsSearch, string? Error) { public bool Allowed => Uri != null; }
public record BrowserContext(Guid TabId, long DocumentVersion, string Origin);
public enum ActionKind { OpenUrl, BookmarkCurrent, SetTextScale, SetContrast }
public record AssistantAction(ActionKind Kind, string? Value = null);
public record ActionProposal(Guid Id, AssistantAction Action, BrowserContext Context, DateTimeOffset ExpiresAt);
public record GuideReply(string Text, AssistantAction? Action = null);
public record Bookmark(string Title, string Url);
public record SettingsResult(BrowserSettings Settings, string? Error = null);
