using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Input;
using Optimus.Core;

namespace Optimus.App;

/// <summary>Native start surface. All actions return to the tab's existing navigation gates.</summary>
internal sealed class NativeHomeView : UserControl
{
    private readonly TextBox query = new() { MaxLength = 500, MinHeight = 60, VerticalContentAlignment = VerticalAlignment.Center };
    private readonly ComboBox source = new() { MinHeight = 44 };

    public NativeHomeView(bool isPrivate, Func<string, OptimusSearchScope, Task> submit, Action openIndex, Action bookmarks, Action help)
    {
        NativeSurface.Surface(this);
        var body = new StackPanel { MaxWidth = 1000, Margin = new Thickness(40, 32, 40, 32), HorizontalAlignment = HorizontalAlignment.Stretch };
        var identity = new WrapPanel { Margin = new Thickness(0, 0, 0, 28) };
        var logo = new Image { Height = 56, Width = 56, Margin = new Thickness(0, 0, 14, 8) };
        logo.SetResourceReference(Image.SourceProperty, "OptimusLogo");
        AutomationProperties.SetName(logo, "Optimus");
        identity.Children.Add(logo);
        var brand = NativeSurface.Text("OPTIMUS", "OptimusBodySize");
        brand.FontWeight = FontWeights.SemiBold;
        brand.VerticalAlignment = VerticalAlignment.Center;
        brand.Margin = new Thickness(0, 0, 18, 8);
        identity.Children.Add(brand);
        var mode = NativeSurface.Text(isPrivate ? "Pestaña privada" : "Tu espacio de inicio", "OptimusSmallSize", "OptimusAccentBrush");
        mode.VerticalAlignment = VerticalAlignment.Center;
        mode.Margin = new Thickness(0, 0, 0, 8);
        identity.Children.Add(mode);
        body.Children.Add(identity);

        var headline = NativeSurface.Text("Menos ruido. Más tú.", "OptimusTitleSize");
        headline.FontWeight = FontWeights.SemiBold;
        body.Children.Add(headline);
        var intro = NativeSurface.Text("Un lugar tranquilo para empezar. Elige dónde buscar y sigue tu curiosidad.", "OptimusBodySize", "OptimusMutedBrush");
        intro.Margin = new Thickness(0, 12, 0, 28);
        body.Children.Add(intro);

        var form = new StackPanel();
        var label = NativeSurface.Text("¿Qué quieres encontrar?", "OptimusBodySize");
        label.Margin = new Thickness(0, 0, 0, 10);
        form.Children.Add(label);
        NativeSurface.Input(query);
        AutomationProperties.SetName(query, "Consulta de inicio de Optimus");
        query.ToolTip = "Hasta 500 caracteres. Pulsa Intro para buscar en la fuente elegida.";
        query.Margin = new Thickness(0, 0, 0, 12);
        form.Children.Add(query);
        source.Items.Add("Web"); source.Items.Add("Índice Optimus"); source.Items.Add("Wikipedia"); source.SelectedIndex = 0;
        NativeSurface.Input(source);
        AutomationProperties.SetName(source, "Fuente de búsqueda de inicio");
        var controls = new Grid();
        controls.ColumnDefinitions.Add(new ColumnDefinition());
        controls.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        controls.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        controls.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        controls.Children.Add(source);
        var search = NativeSurface.Button("Buscar", "Buscar en la fuente elegida", true);
        controls.Children.Add(search);
        form.Children.Add(controls);
        var sourceNote = NativeSurface.Text("", "OptimusSmallSize", "OptimusMutedBrush");
        sourceNote.Margin = new Thickness(0, 12, 0, 0);
        void DescribeSource() => sourceNote.Text = source.SelectedIndex switch
        {
            1 => "Índice local: solo documentos importados. No cubre toda la web.",
            2 => "Wikipedia recibe tu consulta y tu conexión al buscar.",
            _ => "Web usa el servidor del operador. Requiere que esté configurado."
        };
        source.SelectionChanged += (_, _) => DescribeSource();
        DescribeSource();
        form.Children.Add(sourceNote);
        body.Children.Add(NativeSurface.Card(form, new Thickness(24)));
        async Task Submit() => await submit(query.Text, (OptimusSearchScope)Math.Max(0, source.SelectedIndex));
        search.Click += async (_, _) => await Submit();
        query.KeyDown += async (_, e) => { if (e.Key == Key.Enter) { e.Handled = true; await Submit(); } };

        var cards = new Grid { Margin = new Thickness(0, 24, 0, 24) };
        for (var i = 0; i < 3; i++)
        {
            cards.ColumnDefinitions.Add(new ColumnDefinition());
            cards.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        }
        var index = Entry("Tu índice", "Busca entre los documentos importados.", openIndex);
        var saved = Entry("Guardados", "Vuelve a tus marcadores.", bookmarks);
        var guidance = Entry("Ayuda", "Conoce los controles y la privacidad.", help);
        cards.Children.Add(index); cards.Children.Add(saved); cards.Children.Add(guidance);
        body.Children.Add(cards);

        body.Children.Add(NativeSurface.Text(isPrivate
            ? "Privado: las direcciones de esta pestaña no se guardan en la sesión. No ofrece anonimato."
            : "Tú eliges el destino. Optimus no guarda un historial general de navegación.", "OptimusSmallSize", "OptimusMutedBrush"));
        var detailHeader = NativeSurface.Text("Sobre este espacio", "OptimusSmallSize");
        detailHeader.MinHeight = 44;
        detailHeader.VerticalAlignment = VerticalAlignment.Center;
        var detail = new Expander { Header = detailHeader, MinHeight = 44, Margin = new Thickness(0, 8, 0, 0) };
        AutomationProperties.SetName(detail, "Detalles de privacidad del inicio");
        detail.Content = NativeSurface.Text((isPrivate
            ? "Los marcadores y las descargas que guardes explícitamente pueden conservarse. "
            : "Las cookies y los datos de sitios pueden persistir. Restaurar direcciones requiere activar esa opción. ")
            + "La comprobación de reputación se solicita al motor; Windows puede modificar su funcionamiento.", "OptimusSmallSize", "OptimusMutedBrush");
        body.Children.Add(detail);
        Content = new ScrollViewer { Content = body, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled };
        double previousWidth = -1, previousScale = -1;
        void Reflow()
        {
            var scale = Math.Max(1, query.FontSize / 18);
            if (previousWidth == ActualWidth && previousScale == scale) return;
            previousWidth = ActualWidth; previousScale = scale;
            var compact = ActualWidth / scale < 680;
            body.Margin = compact ? new Thickness(18, 24, 18, 24) : new Thickness(40, 32, 40, 32);
            Grid.SetRow(search, compact ? 1 : 0); Grid.SetColumn(search, compact ? 0 : 1);
            Grid.SetColumnSpan(source, compact ? 2 : 1); Grid.SetColumnSpan(search, compact ? 2 : 1);
            search.Margin = compact ? new Thickness(0, 12, 0, 0) : new Thickness(12, 0, 0, 0);
            for (var i = 0; i < cards.Children.Count; i++)
            {
                var card = (FrameworkElement)cards.Children[i];
                Grid.SetRow(card, compact ? i : 0); Grid.SetColumn(card, compact ? 0 : i);
                Grid.SetColumnSpan(card, compact ? 3 : 1);
                card.Margin = compact ? new Thickness(0, 0, 0, 12) : new Thickness(i == 0 ? 0 : 8, 0, i == 2 ? 0 : 8, 0);
            }
        }
        SizeChanged += (_, _) => Reflow();
        LayoutUpdated += (_, _) => Reflow();
    }

    public void ClearQuery() => query.Clear();

    private static Button Entry(string title, string description, Action action)
    {
        var content = new StackPanel();
        var heading = NativeSurface.Text(title, "OptimusBodySize");
        heading.FontWeight = FontWeights.SemiBold;
        content.Children.Add(heading);
        var summary = NativeSurface.Text(description, "OptimusSmallSize", "OptimusMutedBrush");
        summary.Margin = new Thickness(0, 8, 0, 0);
        content.Children.Add(summary);
        var button = NativeSurface.Button(title, title);
        button.Content = content;
        button.HorizontalContentAlignment = HorizontalAlignment.Stretch;
        button.VerticalContentAlignment = VerticalAlignment.Top;
        button.Padding = new Thickness(20);
        button.Click += (_, _) => action();
        return button;
    }
}

/// <summary>Resource references stay live when contrast or text scale changes.</summary>
internal static class NativeSurface
{
    public static void Surface(Control control)
    {
        control.SetResourceReference(Control.BackgroundProperty, "OptimusPageBrush");
        control.SetResourceReference(Control.ForegroundProperty, "OptimusTextBrush");
        control.SetResourceReference(Control.FontSizeProperty, "OptimusBodySize");
    }

    public static TextBlock Text(string text, string size = "OptimusBodySize", string brush = "OptimusTextBrush")
    {
        var block = new TextBlock { Text = text, TextWrapping = TextWrapping.Wrap };
        block.SetResourceReference(TextBlock.FontSizeProperty, size);
        block.SetResourceReference(TextBlock.ForegroundProperty, brush);
        return block;
    }

    public static void Input(Control control)
    {
        control.SetResourceReference(Control.BackgroundProperty, "OptimusRaisedBrush");
        control.SetResourceReference(Control.ForegroundProperty, "OptimusTextBrush");
        control.SetResourceReference(Control.BorderBrushProperty, "OptimusBorderBrush");
        control.SetResourceReference(Control.FontSizeProperty, "OptimusBodySize");
        control.Padding = new Thickness(12, 8, 12, 8);
    }

    public static Button Button(string text, string name, bool primary = false)
    {
        var button = new Button { Content = Text(text, "OptimusBodySize", primary ? "OptimusOnAccentBrush" : "OptimusTextBrush"), MinHeight = 44, Padding = new Thickness(16, 10, 16, 10), Margin = new Thickness(0) };
        Input(button);
        if (primary) button.SetResourceReference(Control.BackgroundProperty, "OptimusWarmBrush");
        AutomationProperties.SetName(button, name);
        return button;
    }

    public static Border Card(UIElement content, Thickness padding)
    {
        var border = new Border { Child = content, Padding = padding, BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(16) };
        border.SetResourceReference(Border.BackgroundProperty, "OptimusPanelBrush");
        border.SetResourceReference(Border.BorderBrushProperty, "OptimusBorderBrush");
        return border;
    }
}
