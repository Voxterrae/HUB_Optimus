using System.Windows;
using System.Windows.Controls;
using Optimus.Core;

namespace Optimus.App;

// Compiled only into the regression executable. No test hooks enter Optimus.App.
public partial class MainWindow
{
    private bool testDisposed;
    internal void TestPreventPersistence() => closed = true;

    internal BrowserTab TestAttach(BrowserSettings fixture,
        Func<CancellationToken, Task<SearchHostConnection>> connect, List<string> openings)
    {
        settings = fixture;
        privacy = new(fixture.PrivacyRules);
        var tab = new BrowserTab(_ => throw new InvalidOperationException("Unexpected recovery."),
            false, () => privacy, () => policyGeneration, () => settings.Bookmarks, "Regression",
            t => Owns(t) && Active == t && !closing && !clearingData && !profileGate.IsBlocked,
            lifetime.Token, connect, pilotCatalog,
            _ => throw new InvalidOperationException("Unexpected catalog change."), () => false);
        // Exercise the real navigation policy/handler. Creation/engine initialization is
        // deliberately excluded; this is not evidence for CreateTabAsync's event wiring.
        tab.OpenRequested += (sender, address) =>
        {
            openings.Add(address);
            if (Active == sender) NavigateKnownGet(sender, address);
        };
        Tabs.Items.Add(tab.Item);
        Tabs.SelectedItem = tab.Item;
        return tab;
    }

    internal BrowserSettings TestSettings => settings;
    internal TextBox TestAddress => Address;
    internal string TestStatus => Status.Text;
    internal bool TestHostStarted => searchHost.OwnsProcess;

    internal void TestDispose()
    {
        if (testDisposed) return;
        testDisposed = true;
        // Window_Closing saves settings even for a never-shown window. Avoid that path.
        closed = true;
        closing = true;
        timer.Stop();
        lifetime.Dispose();
        if (Tabs is not null)
        {
            foreach (var item in Tabs.Items.Cast<TabItem>().ToArray())
                if (item.Tag is BrowserTab tab) tab.Dispose();
            Tabs.Items.Clear();
        }
        searchHost.Dispose();
        pilotCatalog.Dispose();
        searchConnectionClient.Dispose();
        Close(); // Also detaches the native appearance notifications via Closed.
    }
}
