using System.Net.Http;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Optimus.Core;

namespace Optimus.App;

/// <summary>A transient native surface. Queries/results never enter a WebView or settings.</summary>
internal sealed class OptimusSearchView : UserControl, IDisposable
{
    private readonly Action<string> _openUrl;
    private readonly PublicPilotCatalog _pilot;
    private readonly Func<bool, Task<PilotCatalogChange>> _changePilot;
    private readonly Func<bool> _catalogBusy;
    private readonly StackPanel _pilotPanel = new();
    private readonly TextBlock _pilotScope = NativeSurface.Text("Catálogo habitual", "OptimusSmallSize");
    private readonly Button _loadPilot = NativeSurface.Button("Cargar catálogo piloto", "Cargar catálogo piloto");
    private readonly Button _restorePilot = NativeSurface.Button("Restaurar catálogo anterior", "Restaurar catálogo anterior");
    private readonly Func<IReadOnlyList<Bookmark>> _bookmarks;
    private readonly HttpClient _client;
    private readonly SearchSubmissionGate _submissions;
    public bool CanSubmit=>!_disposed&&_submissions.CanSubmit;
    private readonly TextBox _query = new() { MaxLength = 500, MinHeight = 44, VerticalContentAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 8, 0) };
    private readonly TextBlock _status = new() { TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 12, 0, 12) };
    private readonly TextBlock _privacy = new() { TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 8, 0, 8) };
    private readonly TextBlock _privacyDetails = new() { TextWrapping = TextWrapping.Wrap };
    private readonly StackPanel _results = new();
    private CancellationTokenSource? _pending;
    private readonly ComboBox _scope = new() { MinHeight = 44, Margin = new Thickness(0, 0, 0, 8) };
    private readonly Func<CancellationToken, Task<SearchHostConnection>> _connect;
    private readonly CancellationToken _hostLifetime;
    private OptimusSearchScope Scope => (OptimusSearchScope)Math.Max(0, _scope.SelectedIndex);
    private long _generation;
    private bool _disposed;

    public OptimusSearchView(Action<string> openUrl, Func<IReadOnlyList<Bookmark>> bookmarks,Func<bool> eligible,CancellationToken hostLifetime,Func<CancellationToken,Task<SearchHostConnection>> connect,PublicPilotCatalog pilot,Func<bool,Task<PilotCatalogChange>> changePilot,Func<bool> catalogBusy)
    {
        _openUrl = openUrl; _pilot = pilot; _changePilot = changePilot; _catalogBusy = catalogBusy;
        _connect = connect;
        _hostLifetime = hostLifetime;
        _bookmarks = bookmarks;
        _client = new HttpClient(new HttpClientHandler
        {
            AllowAutoRedirect = false,
            UseCookies = false,
            UseDefaultCredentials = false,
            Credentials = null,
            UseProxy = false
        });
        _submissions = new SearchSubmissionGate(new OptimusSearchService(_client),eligible,hostLifetime);
        NativeSurface.Surface(this);
        NativeSurface.Input(_query);
        NativeSurface.Input(_scope);
        _query.Margin = new Thickness(0, 0, 0, 12);
        _query.MinHeight = 60;
        _scope.Margin = new Thickness(0);
        _status.SetResourceReference(TextBlock.ForegroundProperty, "OptimusMutedBrush");
        _status.SetResourceReference(TextBlock.FontSizeProperty, "OptimusBodySize");
        foreach (var text in new[] { _privacy, _privacyDetails })
        {
            text.SetResourceReference(TextBlock.ForegroundProperty, "OptimusMutedBrush");
            text.SetResourceReference(TextBlock.FontSizeProperty, "OptimusSmallSize");
        }
        var body = new StackPanel { MaxWidth = 1000, Margin = new Thickness(40, 32, 40, 32) };
        var title = NativeSurface.Text("Encuentra tu próximo paso.", "OptimusTitleSize");
        title.FontWeight = FontWeights.SemiBold;
        body.Children.Add(title);
        var subtitle = NativeSurface.Text("Optimus Search · elige una fuente y busca con intención.", "OptimusBodySize", "OptimusMutedBrush");
        subtitle.Margin = new Thickness(0, 12, 0, 24);
        body.Children.Add(subtitle);
        var searchPanel = new StackPanel();
        searchPanel.Children.Add(_query);
        _scope.Items.Add("Web"); _scope.Items.Add("Índice Optimus"); _scope.Items.Add("Wikipedia"); _scope.SelectedIndex = 0;
        System.Windows.Automation.AutomationProperties.SetName(_scope, "Fuente de búsqueda");
        _scope.SelectionChanged += (_, _) => { Invalidate(); _results.Children.Clear(); UpdatePrivacy(); _status.Text = "Fuente cambiada. Pulsa Buscar para consultar."; };
        _query.TextChanged += (_, _) => { Invalidate(); _results.Children.Clear(); _status.Text = "Consulta modificada. Pulsa Buscar para consultar."; };
        _pilotPanel.Children.Add(_pilotScope);
        _pilotPanel.Children.Add(NativeSurface.Text("Piloto público en español · solo esta sesión · no cubre toda Internet.", "OptimusSmallSize", "OptimusMutedBrush"));
        var pilotActions = new WrapPanel();
        foreach (var button in new[] { _loadPilot, _restorePilot }) { button.Margin = new Thickness(0, 8, 8, 8); pilotActions.Children.Add(button); }
        _pilotPanel.Children.Add(pilotActions);
        _loadPilot.Click += async (_, _) => await ChangePilotAsync(true);
        _restorePilot.Click += async (_, _) => await ChangePilotAsync(false);
        UpdatePrivacy();
        var form = new Grid();
        form.ColumnDefinitions.Add(new ColumnDefinition());
        form.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        form.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        form.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        _query.ToolTip = "Consulta: hasta 500 caracteres. Pulsa Intro para buscar.";
        System.Windows.Automation.AutomationProperties.SetName(_query, "Consulta de Optimus Search");
        form.Children.Add(_scope);
        var submit = NativeSurface.Button("Buscar", "Buscar en la fuente elegida", true);
        Grid.SetColumn(submit, 1);
        form.Children.Add(submit);
        submit.Click += async (_, _) => await SearchAsync(_query.Text, Scope);
        _query.KeyDown += async (_, e) =>
        {
            if (e.Key != Key.Enter) return;
            e.Handled = true;
            await SearchAsync(_query.Text, Scope);
        };
        searchPanel.Children.Add(form);
        searchPanel.Children.Add(_privacy);
        searchPanel.Children.Add(_pilotPanel);
        var detailHeader = NativeSurface.Text("Detalles de la fuente y privacidad", "OptimusSmallSize");
        detailHeader.MinHeight = 44;
        detailHeader.VerticalAlignment = VerticalAlignment.Center;
        var privacyDetail = new Expander { Header = detailHeader, MinHeight = 44, Content = _privacyDetails };
        System.Windows.Automation.AutomationProperties.SetName(privacyDetail, "Detalles de la fuente y privacidad");
        searchPanel.Children.Add(privacyDetail);
        body.Children.Add(NativeSurface.Card(searchPanel, new Thickness(24)));
        _status.Text = "Escribe una consulta y pulsa Buscar.";
        System.Windows.Automation.AutomationProperties.SetLiveSetting(_status, System.Windows.Automation.AutomationLiveSetting.Polite);
        body.Children.Add(_status);
        body.Children.Add(_results);
        Content = new ScrollViewer { Content = body, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled };
        double previousWidth = -1, previousScale = -1;
        void Reflow()
        {
            var scale = Math.Max(1, _query.FontSize / 18);
            if (previousWidth == ActualWidth && previousScale == scale) return;
            previousWidth = ActualWidth; previousScale = scale;
            var compact = ActualWidth / scale < 680;
            body.Margin = compact ? new Thickness(18, 24, 18, 24) : new Thickness(40, 32, 40, 32);
            Grid.SetRow(submit, compact ? 1 : 0); Grid.SetColumn(submit, compact ? 0 : 1);
            Grid.SetColumnSpan(_scope, compact ? 2 : 1); Grid.SetColumnSpan(submit, compact ? 2 : 1);
            submit.Margin = compact ? new Thickness(0, 12, 0, 0) : new Thickness(12, 0, 0, 0);
        }
        SizeChanged += (_, _) => Reflow();
        LayoutUpdated += (_, _) => Reflow();
    }

    public async Task SearchAsync(string query, OptimusSearchScope scope, CancellationToken token = default)
    {
        if(!CanSubmit)return;
        Invalidate();
        _scope.SelectedIndex = (int)scope;
        _query.Text = query;
        var generation = _generation;
        UpdatePrivacy();
        _results.Children.Clear();
        _status.Text = scope switch { OptimusSearchScope.Index => "Buscando en el índice local…", OptimusSearchScope.Wikipedia => "Buscando en Wikipedia…", _ => "Preparando la búsqueda Web local…" };
        using var cancellation = CancellationTokenSource.CreateLinkedTokenSource(token, _hostLifetime);
        _pending = cancellation;
        try
        {
            // Host supplies an empty list in private tabs. Capture before the first await.
            if (string.IsNullOrWhiteSpace(query) || query.Length > 500) { _status.Text = "Escribe una consulta de 1 a 500 caracteres."; return; }
            var bookmarks = _bookmarks().ToArray();
            OptimusSearchTarget target = new(scope, null, null);
            if (scope != OptimusSearchScope.Wikipedia)
            {
                var connection = await _connect(cancellation.Token);
                if (!CanSubmit || generation != _generation || cancellation.IsCancellationRequested) return;
                if (connection.Error is {} error) { _status.Text = error; return; }
                target = connection.Target with { Scope = scope };
            }
            var response = await _submissions.SearchAsync(query, bookmarks, target, cancellation.Token);
            if (response is null || !CanSubmit || generation != _generation || cancellation.IsCancellationRequested) return;
            _status.Text = response.Provider + " · " + (response.Error ?? (response.Results.Count == 0 ? "Sin resultados." : $"{response.Results.Count} resultados."));
            foreach (var result in response.Results)
            {
                var row = new StackPanel();
                // Untrusted strings are plain Text values, never XAML, HTML or document markup.
                var heading = NativeSurface.Text(result.Title);
                heading.FontWeight = FontWeights.SemiBold;
                row.Children.Add(heading);
                var address = NativeSurface.Text(result.Source + " · " + result.Url, "OptimusSmallSize", "OptimusAccentBrush");
                address.Margin = new Thickness(0, 8, 0, 0);
                row.Children.Add(address);
                var snippet = NativeSurface.Text(result.Snippet, "OptimusBodySize", "OptimusMutedBrush");
                snippet.Margin = new Thickness(0, 12, 0, 16);
                row.Children.Add(snippet);
                var open = NativeSurface.Button("Abrir resultado", "Abrir: " + result.Title);
                open.HorizontalAlignment = HorizontalAlignment.Stretch;
                System.Windows.Automation.AutomationProperties.SetName(open, "Abrir: " + result.Title);
                open.Click += (_, _) =>
                {
                    if (CanSubmit && generation == _generation) _openUrl(result.Url);
                };
                row.Children.Add(open);
                var card = NativeSurface.Card(row, new Thickness(24));
                card.Margin = new Thickness(0, 0, 0, 16);
                _results.Children.Add(card);
            }
        }
        catch (OperationCanceledException)
        {
            if (!_disposed && generation == _generation)
            {
                _results.Children.Clear();
                _status.Text = "Búsqueda cancelada.";
            }
        }
        finally
        {
            if (ReferenceEquals(_pending, cancellation)) _pending = null;
        }
    }

    private async Task ChangePilotAsync(bool enabled)
    {
        if (_disposed || _catalogBusy() || !CanSubmit) return;
        var result = await _changePilot(enabled);
        if (_disposed || !CanSubmit) return;
        RefreshPilot();
        _status.Text = result.Error ?? (result.Active
            ? "Piloto público cargado para esta sesión. Escribe una consulta y pulsa Buscar."
            : "Catálogo anterior restaurado. Escribe una consulta y pulsa Buscar.");
    }

    public void RefreshPilot()
    {
        _pilotPanel.Visibility = Scope == OptimusSearchScope.Index ? Visibility.Visible : Visibility.Collapsed;
        _pilotScope.Text = _pilot.IsActive ? "Piloto público · 8 documentos" : "Catálogo habitual";
        _loadPilot.IsEnabled = !_catalogBusy() && CanSubmit;
        _restorePilot.IsEnabled = !_catalogBusy() && CanSubmit && _pilot.IsActive;
    }

    private void UpdatePrivacy()
    {
        RefreshPilot();
        _privacy.Text = Scope switch
        {
            OptimusSearchScope.Index => "Índice local · solo documentos importados, sin red.",
            OptimusSearchScope.Wikipedia => "Wikipedia · esta fuente recibe tu consulta y conexión.",
            _ => "Web · usa el servidor del operador; requiere configuración."
        };
        _privacyDetails.Text = Scope switch
    {
        OptimusSearchScope.Index => "Índice Optimus: búsqueda local, sin red. Solo incluye los documentos importados; no cubre toda la web. Los marcadores de esta pestaña se combinan localmente. No se guardan consultas ni resultados.",
        OptimusSearchScope.Wikipedia => "Wikipedia explícita y marcadores locales. Wikipedia recibe tu consulta y conexión y puede aplicar sus políticas de registro. No se guardan consultas ni resultados.",
        _ => "Web: el servicio local consulta el servidor SearXNG del operador, que puede consultar proveedores externos y aplicar sus políticas de registro. Si no está configurado, se muestra un error. No se guardan consultas ni resultados."
        };
    }

    /// <summary>Select an empty search form without connecting or submitting a query.</summary>
    public void SetScope(OptimusSearchScope scope) => _scope.SelectedIndex = (int)scope;

    public void FocusQuery() { if (CanSubmit) { _query.Focus(); _query.SelectAll(); } }

    public void Disable()
    {
        _submissions.Disable();Cancel();IsEnabled=false;Visibility=Visibility.Collapsed;
    }

    public void Cancel()
    {
        Invalidate();
        _query.Clear();
        _results.Children.Clear();
        _status.Text = "Escribe una consulta y pulsa Buscar.";
    }

    private void Invalidate()
    {
        _generation++;
        _submissions.Invalidate();
        _pending?.Cancel();
        _pending = null;
    }

    public void Dispose()
    {
        if (_disposed) return;
        Disable();
        _disposed = true;
        _submissions.Dispose();
        _client.Dispose();
    }
}
