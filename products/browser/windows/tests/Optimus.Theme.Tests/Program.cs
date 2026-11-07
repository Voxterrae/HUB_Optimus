using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;
using System.Windows.Threading;
using Optimus.App;
using Optimus.Core;

internal static class Program
{
    private static int checks;

    [STAThread]
    private static int Main()
    {
        if (!Environment.UserInteractive)
        {
            Console.Error.WriteLine("BLOCKED: an interactive Windows desktop is required.");
            return 2;
        }
        var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
        app.Resources.MergedDictionaries.Add(new ResourceDictionary
        {
            Source = new Uri("/Optimus.Theme.Tests;component/Assets/OptimusTheme.xaml", UriKind.Relative)
        });
        var window = new Window { Title = "Optimus tooltip regression", Width = 420, Height = 200, ShowActivated = false };
        try
        {
            var body = new StackPanel();
            window.Content = body;
            window.Show();
            foreach (var (control, text) in new (Control, string)[]
            {
                (new Button { Style = (Style)app.FindResource("OptimusQuietButton") }, "Atrás · Alt+Izquierda"),
                (new Button { Style = (Style)app.FindResource("OptimusPrimaryButton") }, "Ir o buscar · Intro"),
                (new TextBox(), "Escribe una dirección o busca con Optimus · Ctrl+L"),
                (new TextBox(), "Consulta: hasta 500 caracteres. Pulsa Intro para buscar."),
                (new Button { Style = (Style)app.FindResource("OptimusQuietButton") }, "Menú · pestañas, ayuda y ajustes")
            })
            {
                body.Children.Add(control);
                Exercise(window, control, text);
                body.Children.Remove(control);
            }

            // The settings dialog has its own resources; it must not fall back to app defaults.
            var field = new TextBox();
            var dialog = new Window { Owner = window, Content = field, Width = 320, Height = 160, ShowActivated = false };
            try
            {
                dialog.Show();
                Exercise(dialog, field, "Por ejemplo: example.org o https://example.org", window);
            }
            finally { dialog.Close(); }
            Console.WriteLine($"PASS: {checks} native tooltip checks. Visual acceptance and assistive technology remain separate.");
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine($"FAIL: {error}");
            return 1;
        }
        finally { window.Close(); app.Shutdown(); }
    }

    private static void Exercise(Window window, Control target, string text, Window? owner = null)
    {
        var tooltip = new ToolTip { PlacementTarget = target, Placement = PlacementMode.Bottom, Content = text };
        target.ToolTip = tooltip;
        try
        {
            // Reuse the same open popup across theme changes, then test close/reopen too.
            foreach (var palette in new[] { AppearancePalette.Dark, AppearancePalette.Light, AppearancePalette.HighContrast, AppearancePalette.SystemHighContrast, AppearancePalette.Dark })
            {
                var state = new AppearanceState(palette, 1, false);
                if (owner is null) NativeTheme.Apply(window, state);
                else { NativeTheme.Apply(owner, state); NativeTheme.Inherit(window, owner); }
                tooltip.IsOpen = true;
                Flush(tooltip);
                Verify(tooltip, text, palette);
            }
            tooltip.IsOpen = false;
            NativeTheme.Apply(window, new(AppearancePalette.Light, 1, false));
            tooltip.IsOpen = true;
            Flush(tooltip);
            Verify(tooltip, text, AppearancePalette.Light);
        }
        finally { tooltip.IsOpen = false; target.ToolTip = null; }
    }

    private static void Flush(ToolTip tooltip)
    {
        tooltip.Dispatcher.Invoke(() => { }, DispatcherPriority.ApplicationIdle);
        tooltip.UpdateLayout();
    }

    private static void Verify(ToolTip tooltip, string text, AppearancePalette palette)
    {
        var (background, foreground) = palette switch
        {
            AppearancePalette.Light => (Color.FromRgb(240, 242, 243), Color.FromRgb(24, 33, 43)),
            AppearancePalette.HighContrast => (Colors.Black, Colors.White),
            AppearancePalette.SystemHighContrast => (SystemColors.WindowColor, SystemColors.WindowTextColor),
            _ => (Color.FromRgb(23, 28, 36), Color.FromRgb(245, 242, 236))
        };
        Check(tooltip.IsVisible, $"{palette}: popup is visible");
        Check(ColorOf(tooltip.Background) == background, $"{palette}: popup background uses the window palette (actual {ColorOf(tooltip.Background)})");
        Check(ColorOf(tooltip.Foreground) == foreground, $"{palette}: popup foreground uses the window palette");
        var rendered = Descendants(tooltip).OfType<TextBlock>().Single(block => block.Text == text);
        Check(ColorOf(rendered.Foreground) == foreground, $"{palette}: rendered text uses the window palette");
        var border = Descendants(tooltip).OfType<Border>().First(item => item.Background is SolidColorBrush brush && brush.Color == background);
        Check(border.IsVisible, $"{palette}: native template renders the paired background");
        // Respect a user's OS color choices; the app's own palettes must meet 4.5:1.
        if (palette != AppearancePalette.SystemHighContrast)
            Check(Contrast(ColorOf(rendered.Foreground), ColorOf(border.Background)) >= 4.5, $"{palette}: rendered text contrast >= 4.5:1");
    }

    private static IEnumerable<DependencyObject> Descendants(DependencyObject root)
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(root); i++)
        {
            var child = VisualTreeHelper.GetChild(root, i);
            yield return child;
            foreach (var descendant in Descendants(child)) yield return descendant;
        }
    }

    private static Color ColorOf(Brush brush) => brush is SolidColorBrush solid ? solid.Color : throw new InvalidOperationException("Expected a solid palette brush.");
    private static double Contrast(Color foreground, Color background)
    {
        static double Linear(byte channel) { var s = channel / 255d; return s <= 0.04045 ? s / 12.92 : Math.Pow((s + 0.055) / 1.055, 2.4); }
        static double Luminance(Color c) => 0.2126 * Linear(c.R) + 0.7152 * Linear(c.G) + 0.0722 * Linear(c.B);
        var a = Luminance(foreground); var b = Luminance(background);
        return (Math.Max(a, b) + 0.05) / (Math.Min(a, b) + 0.05);
    }
    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
        checks++;
    }
}
