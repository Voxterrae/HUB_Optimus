using System.Runtime.InteropServices;
using System.Windows.Automation;

namespace Optimus.Windows.Smoke;

internal static class GuiNavigationDiagnostics
{
    // The caller verifies this root belongs to the process it launched. All reads
    // remain inside that root and its native process; no desktop-wide UI search.
    internal static void Capture(AutomationElement window, string expectedAddress, SmokeReport report, string phase)
    {
        if (phase is not ("before-go" or "navigation-failure")) return;
        var snapshot = Snapshot.Unavailable;
        try
        {
            // An unresponsive UIA provider must not hold up the original failure.
            // The worker returns values only; a late completion cannot alter the report.
            snapshot = Task.Run(() => Read(window, expectedAddress)).WaitAsync(TimeSpan.FromSeconds(2)).GetAwaiter().GetResult();
        }
        catch { }
        report.GuiDiagnostics[phase + ".addressMatches"] = snapshot.AddressMatches;
        report.GuiDiagnostics[phase + ".keyboardFocus"] = snapshot.KeyboardFocus;
        report.GuiDiagnostics[phase + ".recoveryVisible"] = snapshot.RecoveryVisible;
        report.GuiDiagnostics[phase + ".status"] = snapshot.Status;
        report.GuiDiagnostics[phase + ".navigationReady"] = snapshot.Navigation.Ready;
        report.GuiDiagnostics[phase + ".preparationStage"] = snapshot.Navigation.Stage;
    }

    internal static bool IsNavigationReady(AutomationElement window)
    {
        try
        {
            return Task.Run(() =>
            {
                var processId = OwnedProcessId(window);
                return processId is { } id && SelectedNavigation(window, id).Ready == "true";
            }).WaitAsync(TimeSpan.FromSeconds(2)).GetAwaiter().GetResult();
        }
        catch { return false; }
    }

    private static Snapshot Read(AutomationElement window, string expectedAddress)
    {
        if (OwnedProcessId(window) is not { } processId) return Snapshot.Unavailable;
        AutomationElement? Find(Condition selector) => window.FindFirst(TreeScope.Descendants,
            new AndCondition(selector, new PropertyCondition(AutomationElement.ProcessIdProperty, processId)));
        var address = Find(new AndCondition(new PropertyCondition(AutomationElement.AutomationIdProperty, "Address"),
            new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Edit)));
        var matches = "unavailable";
        if (address is not null && address.TryGetCurrentPattern(ValuePattern.Pattern, out var value))
            matches = Boolean(string.Equals(((ValuePattern)value).Current.Value, expectedAddress, StringComparison.Ordinal));
        var focus = address is null ? "unavailable" : Boolean(address.Current.HasKeyboardFocus);
        var recovery = Find(new AndCondition(new PropertyCondition(AutomationElement.NameProperty, "Recuperar esta pestaña"),
            new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Button),
            new PropertyCondition(AutomationElement.IsOffscreenProperty, false)));
        var status = Find(new AndCondition(new PropertyCondition(AutomationElement.AutomationIdProperty, "Status"),
            new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Text)));
        return new(matches, focus, Boolean(recovery is not null), status is null ? "unavailable" : ClassifyStatus(status.Current.Name), SelectedNavigation(window, processId));
    }

    private static int? OwnedProcessId(AutomationElement window)
    {
        var processId = window.Current.ProcessId;
        var handle = (nint)window.Current.NativeWindowHandle;
        return processId > 0 && handle != 0 && GetWindowThreadProcessId(handle, out var owner) != 0 && owner == (uint)processId ? processId : null;
    }

    private static NavigationState SelectedNavigation(AutomationElement window, int processId)
    {
        var selected = window.FindFirst(TreeScope.Descendants, new AndCondition(
            new PropertyCondition(AutomationElement.ProcessIdProperty, processId),
            new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.TabItem),
            new PropertyCondition(SelectionItemPattern.IsSelectedProperty, true)));
        return selected?.Current.ItemStatus switch
        {
            "Preparando navegador" => new("false", "engine"),
            "Preparando datos de navegación" => new("false", "profile"),
            "Listo para navegar" => new("true", "ready"),
            "Navegación no disponible" => new("false", "stopped"),
            _ => NavigationState.Unavailable
        };
    }

    private static string Boolean(bool value) => value ? "true" : "false";

    private static string ClassifyStatus(string text)
    {
        if (text.StartsWith("No se pudo iniciar WebView2.", StringComparison.Ordinal)) return "engine-initialization-failed";
        if (text.StartsWith("No se pudo verificar el perfil y su barrera de privacidad.", StringComparison.Ordinal)) return "profile-initialization-failed";
        if (text.StartsWith("El perfil está bloqueado.", StringComparison.Ordinal)
            || text.StartsWith("El perfil está ocupado o requiere reiniciar", StringComparison.Ordinal)
            || text.StartsWith("La barrera no pudo verificar", StringComparison.Ordinal)
            || text.StartsWith("No se verificó el cierre del controlador.", StringComparison.Ordinal)) return "profile-blocked";
        if (text.StartsWith("La pestaña aún no está preparada.", StringComparison.Ordinal)
            || text.StartsWith("Espera a que termine la preparación del perfil", StringComparison.Ordinal)) return "navigation-unready";
        if (text.StartsWith("El motor se detuvo.", StringComparison.Ordinal)) return "engine-failed";
        if (text.StartsWith("El motor no pudo abrir la dirección.", StringComparison.Ordinal)
            || text.StartsWith("El motor no pudo completar la acción.", StringComparison.Ordinal)
            || text.StartsWith("No se cargó la página (", StringComparison.Ordinal)) return "navigation-error";
        if (text.StartsWith("Destino bloqueado por una regla local.", StringComparison.Ordinal)
            || text.StartsWith("Navegación protegida cancelada.", StringComparison.Ordinal)
            || text.StartsWith("Usa los controles de Optimus para elegir el perfil", StringComparison.Ordinal)) return "navigation-policy-blocked";
        if (text.StartsWith("Solo se permiten direcciones completas HTTP o HTTPS.", StringComparison.Ordinal)
            || text.StartsWith("La dirección", StringComparison.Ordinal)
            || text.StartsWith("Dirección HTTP o HTTPS no válida.", StringComparison.Ordinal)
            || text.StartsWith("Escribe una dirección o una búsqueda.", StringComparison.Ordinal)) return "address-rejected";
        if (text.StartsWith("Optimus ", StringComparison.Ordinal) && text.EndsWith("Listo para empezar.", StringComparison.Ordinal)) return "default-notice";
        return string.IsNullOrEmpty(text) ? "empty" : "other";
    }

    private sealed record NavigationState(string Ready, string Stage)
    {
        public static NavigationState Unavailable { get; } = new("unavailable", "unavailable");
    }

    private sealed record Snapshot(string AddressMatches, string KeyboardFocus, string RecoveryVisible, string Status, NavigationState Navigation)
    {
        public static Snapshot Unavailable { get; } = new("unavailable", "unavailable", "unavailable", "unavailable", NavigationState.Unavailable);
    }

    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(nint hwnd, out uint processId);
}
