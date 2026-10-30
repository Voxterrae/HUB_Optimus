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
    private readonly Func<IReadOnlyList<Bookmark>> _bookmarks;
    private readonly HttpClient _client;
    private readonly SearchSubmissionGate _submissions;
    public bool CanSubmit=>!_disposed&&_submissions.CanSubmit;
    private readonly TextBox _query = new() { MaxLength = 500, MinHeight = 44, VerticalContentAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 8, 0) };
    private readonly TextBlock _status = new() { TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 12, 0, 12) };
    private readonly TextBlock _privacy = new() { TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 8, 0, 8) };
    private readonly StackPanel _results = new();
    private CancellationTokenSource? _pending;
    private readonly ComboBox _scope = new() { MinHeight = 44, Margin = new Thickness(0, 0, 0, 8) };
    private readonly Func<CancellationToken, Task<SearchHostConnection>> _connect;
    private readonly CancellationToken _hostLifetime;
    private OptimusSearchScope Scope => (OptimusSearchScope)Math.Max(0, _scope.SelectedIndex);
    private long _generation;
    private bool _disposed;

    public OptimusSearchView(Action<string> openUrl, Func<IReadOnlyList<Bookmark>> bookmarks,Func<bool> eligible,CancellationToken hostLifetime,Func<CancellationToken,Task<SearchHostConnection>> connect)
    {
        _openUrl = openUrl;
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
        SetResourceReference(BackgroundProperty, SystemColors.WindowBrushKey);
        SetResourceReference(ForegroundProperty, SystemColors.WindowTextBrushKey);

        var body = new StackPanel { MaxWidth = 900, Margin = new Thickness(24) };
        body.Children.Add(new TextBlock { Text = "Optimus Search", FontSize = 28, FontWeight = FontWeights.SemiBold });
        _scope.Items.Add("Web"); _scope.Items.Add("Índice Optimus"); _scope.Items.Add("Wikipedia"); _scope.SelectedIndex = 0;
        System.Windows.Automation.AutomationProperties.SetName(_scope, "Fuente de búsqueda");
        body.Children.Add(_scope);
        _scope.SelectionChanged += (_, _) => { Invalidate(); _results.Children.Clear(); UpdatePrivacy(); _status.Text = "Fuente cambiada. Pulsa Buscar para consultar."; };
        _query.TextChanged += (_, _) => { Invalidate(); _results.Children.Clear(); _status.Text = "Consulta modificada. Pulsa Buscar para consultar."; };
        UpdatePrivacy();
        body.Children.Add(_privacy);
        var form = new Grid();
        form.ColumnDefinitions.Add(new ColumnDefinition());
        form.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        _query.ToolTip = "Consulta: hasta 500 caracteres. Pulsa Intro para buscar.";
        System.Windows.Automation.AutomationProperties.SetName(_query, "Consulta de Optimus Search");
        form.Children.Add(_query);
        var submit = new Button { Content = "Buscar", MinWidth = 100, MinHeight = 44 };
        Grid.SetColumn(submit, 1);
        form.Children.Add(submit);
        submit.Click += async (_, _) => await SearchAsync(_query.Text, Scope);
        _query.KeyDown += async (_, e) =>
        {
            if (e.Key != Key.Enter) return;
            e.Handled = true;
            await SearchAsync(_query.Text, Scope);
        };
        body.Children.Add(form);
        _status.Text = "Escribe una consulta y pulsa Buscar.";
        System.Windows.Automation.AutomationProperties.SetLiveSetting(_status, System.Windows.Automation.AutomationLiveSetting.Polite);
        body.Children.Add(_status);
        body.Children.Add(_results);
        Content = new ScrollViewer { Content = body, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled };
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
                var row = new StackPanel { Margin = new Thickness(0, 0, 0, 16) };
                // Untrusted strings are plain Text values, never XAML, HTML or document markup.
                row.Children.Add(new TextBlock { Text = result.Title, FontSize = 18, FontWeight = FontWeights.SemiBold, TextWrapping = TextWrapping.Wrap });
                row.Children.Add(new TextBlock { Text = result.Source + " · " + result.Url, TextWrapping = TextWrapping.Wrap });
                row.Children.Add(new TextBlock { Text = result.Snippet, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 4, 0, 4) });
                var open = new Button { Content = "Abrir resultado", MinHeight = 44, MinWidth = 140, HorizontalAlignment = HorizontalAlignment.Left };
                System.Windows.Automation.AutomationProperties.SetName(open, "Abrir: " + result.Title);
                open.Click += (_, _) =>
                {
                    if (CanSubmit && generation == _generation) _openUrl(result.Url);
                };
                row.Children.Add(open);
                _results.Children.Add(row);
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

    private void UpdatePrivacy() => _privacy.Text = Scope switch
    {
        OptimusSearchScope.Index => "Índice Optimus: búsqueda local, sin red. Solo incluye los documentos importados; no cubre toda la web. Los marcadores de esta pestaña se combinan localmente. No se guardan consultas ni resultados.",
        OptimusSearchScope.Wikipedia => "Wikipedia explícita y marcadores locales. Wikipedia recibe tu consulta y conexión y puede aplicar sus políticas de registro. No se guardan consultas ni resultados.",
        _ => "Web: el servicio local consulta el servidor SearXNG del operador, que puede consultar proveedores externos y aplicar sus políticas de registro. Si no está configurado, se muestra un error. No se guardan consultas ni resultados."
    };

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
