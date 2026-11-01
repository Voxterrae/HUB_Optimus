using System;
using System.IO;
using System.Text.Json;
using Optimus.Core;

static class WebSearchSettingsTests
{
    public static void Register(Action<string, Action> test)
    {
        test("Web selection survives a real settings save and reload", () => WithStore("{\"WebProvider\":1}", (store, path) =>
        {
            var loaded = store.Load(); Require(loaded.Error is null, "Valid pilot selection loads");
            Require(store.Save(loaded.Settings) is null, "Selection saves");
            using var json = JsonDocument.Parse(File.ReadAllText(path));
            Require(json.RootElement.TryGetProperty("WebProvider", out var provider) && provider.GetInt32() == 1, "Saving must retain explicit Mwmbl selection for the next launch");
        }));
        test("Explicit Web off survives with a remembered operator endpoint", () => WithStore("{\"WebProvider\":0,\"SearxEndpoint\":\"https://operator.example/search\"}", (store, path) =>
        {
            var loaded = store.Load(); Require(loaded.Error is null && store.Save(loaded.Settings) is null, "Explicit off can retain a valid remembered endpoint");
            using var json = JsonDocument.Parse(File.ReadAllText(path));
            Require(json.RootElement.TryGetProperty("WebProvider", out var provider) && provider.GetInt32() == 0, "Do not lose explicit off and reactivate the remembered endpoint on restart");
            Require(json.RootElement.GetProperty("SearxEndpoint").GetString() == "https://operator.example/search", "Remember the server for a later explicit choice");
        }));
        test("Legacy operator endpoint migrates to an explicit Web selection", () => WithStore("{\"SearxEndpoint\":\"https://operator.example/\"}", (store, path) =>
        {
            var loaded = store.Load(); Require(loaded.Error is null && store.Save(loaded.Settings) is null, "Legacy server remains usable");
            using var json = JsonDocument.Parse(File.ReadAllText(path));
            Require(json.RootElement.TryGetProperty("WebProvider", out var provider) && provider.GetInt32() == 2, "Materialize legacy SearXNG selection instead of silently disabling it");
        }));
        test("Unknown Web selection preserves the invalid settings file", () => WithStore("{\"WebProvider\":999}", (store, path) =>
        {
            var before = File.ReadAllText(path);
            Require(store.Load().Error is not null && store.Save(new()) is not null && File.ReadAllText(path) == before, "Unknown provider must fail closed without overwriting the file");
        }));
        test("Selected operator Web source requires its endpoint", () => WithStore("{\"WebProvider\":2}", (store, path) =>
        {
            var before = File.ReadAllText(path);
            Require(store.Load().Error is not null && store.Save(new()) is not null && File.ReadAllText(path) == before, "A selected SearXNG source without a server is invalid and preserved");
        }));
        test("Failed settings apply retains the active policy and source", () => WithStore("{\"WebProvider\":0}", (store, path) =>
        {
            var current = store.Load().Settings;
            var candidate = current with { WebProvider = WebProvider.Mwmbl, PrivacyRules = [new("private.example", PrivacyAction.Block)] };
            File.WriteAllText(path, "{damaged");
            var result = store.Apply(current, candidate);
            Require(result.Error is not null && ReferenceEquals(result.Settings, current), "Persistence failure must return the previous active state, including policy and Web source");
            Require(File.ReadAllText(path) == "{damaged", "Failed apply must preserve the original file");
        }));
        test("Successful settings apply activates only the sanitized saved candidate", () => WithStore("{\"WebProvider\":0}", (store, path) =>
        {
            var current = store.Load().Settings;
            var candidate = current with { WebProvider = WebProvider.Mwmbl, PrivacyRules = [new("private.example", PrivacyAction.Private)], RestoreSession = true, SessionUrls = ["https://private.example/secret"] };
            var result = store.Apply(current, candidate);
            Require(result.Error is null && result.Settings.WebProvider == WebProvider.Mwmbl && result.Settings.SessionUrls.Count == 0, "Apply the persisted policy and sanitized session only after successful storage");
            var loaded = store.Load();
            Require(loaded.Error is null && loaded.Settings.WebProvider == WebProvider.Mwmbl && loaded.Settings.SessionUrls.Count == 0, "Disk and active source must agree after restart");
        }));
    }

    private static void Require(bool valid, string message) { if (!valid) throw new Exception(message); }
    private static void WithStore(string source, Action<SettingsStore, string> action)
    {
        var directory = Path.Combine(Path.GetTempPath(), "optimus-web-settings-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory); var path = Path.Combine(directory, "settings.json");
        try { File.WriteAllText(path, source); action(new SettingsStore(path), path); }
        finally { Directory.Delete(directory, true); }
    }
}
