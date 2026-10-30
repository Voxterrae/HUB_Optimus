using System.Globalization;
namespace Optimus.Core;
public enum NavigationDisposition { Navigate, OpenPrivate, OfferPrivate, Block }
public enum PrivacyAction { Allow, Private, Block }
public record PrivacyRule(string Domain, PrivacyAction Action, bool IncludeSubdomains=true);
/// <summary>Local host rules only; these do not classify pages or promise network isolation.</summary>
public sealed class PrivacyPolicy
{
 private readonly PrivacyRule[] rules;
 public PrivacyPolicy(IEnumerable<PrivacyRule> rules)
 {var items=rules.ToArray();ValidateRules(items);this.rules=items.Select(r=>r with {Domain=NormalizeDomain(r.Domain)}).ToArray();}
 // Declared, intentionally small seed; no sites are visited to install it. Users may remove it.
 public static List<PrivacyRule> Seeds()=>[new("pornhub.com",PrivacyAction.Private),new("xvideos.com",PrivacyAction.Private),new("xnxx.com",PrivacyAction.Private)];
 public static string NormalizeDomain(string domain)
 {
  if(string.IsNullOrEmpty(domain)||domain!=domain.Trim()||domain.Any(c=>char.IsControl(c)||char.IsWhiteSpace(c))||domain.IndexOfAny(['/', '\\', ':', '@', '*', '?', '#', '%'])>=0)throw new ArgumentException("Usa solo un dominio, sin dirección, puerto ni comodines.");
  var host=new IdnMapping().GetAscii(domain.TrimEnd('.')).ToLowerInvariant();
  if(domain.EndsWith("..",StringComparison.Ordinal)||host.Length>253||!host.Contains('.')||host.Split('.').Any(label=>label.Length is <1 or >63||label[0]=='-'||label[^1]=='-'||label.Any(c=>!(char.IsAsciiLetterOrDigit(c)||c=='-')))||Uri.CheckHostName(host)!=UriHostNameType.Dns)throw new ArgumentException("Dominio no válido.");
  return host;
 }
 public static void ValidateRules(IReadOnlyCollection<PrivacyRule> rules)
 {
  if(rules.Count>1000)throw new ArgumentException("Máximo 1000 reglas.");
  foreach(var rule in rules){if(rule==null||rule.Action is not (PrivacyAction.Private or PrivacyAction.Block))throw new ArgumentException("Acción de regla no válida.");NormalizeDomain(rule.Domain);}
 }
 public PrivacyAction Evaluate(Uri uri,bool isPrivate=false,bool worker=false)
 {
  if(!NavigationPolicy.IsAllowed(uri))return PrivacyAction.Block;
  string host;try{host=uri.IdnHost;try{host=NormalizeDomain(host);}catch(ArgumentException){host=host.ToLowerInvariant();}}catch(UriFormatException){return PrivacyAction.Block;}
  bool protect=false;
  foreach(var rule in rules)
  {
   if(host!=rule.Domain&&!(rule.IncludeSubdomains&&host.EndsWith("."+rule.Domain,StringComparison.Ordinal)))continue;
   if(rule.Action==PrivacyAction.Block)return PrivacyAction.Block;protect=true;
  }
  if(worker&&protect)return PrivacyAction.Block;
  return isPrivate||protect?PrivacyAction.Private:PrivacyAction.Allow;
 }
 public NavigationDisposition DecideNavigation(Uri uri,bool isPrivate,bool knownGet)
 {
  var decision=Evaluate(uri,isPrivate);if(decision==PrivacyAction.Block)return NavigationDisposition.Block;
  if(decision==PrivacyAction.Private&&!isPrivate)return knownGet?NavigationDisposition.OpenPrivate:NavigationDisposition.OfferPrivate;
  return NavigationDisposition.Navigate;
 }
 public bool CanPersist(string? address,bool isPrivate=false,bool ephemeral=false)=>!isPrivate&&!ephemeral&&Uri.TryCreate(address,UriKind.Absolute,out var uri)&&NavigationPolicy.IsAllowed(uri)&&Evaluate(uri)==PrivacyAction.Allow;
}
public readonly record struct NavigationLease(long TabGeneration,long PolicyGeneration);
/// <summary>A queued callback must retain both the document epoch and current policy generation.</summary>
public sealed class NavigationEpoch : IDisposable
{
 private long generation;private bool disposed;
 public NavigationLease Capture(long policyGeneration)=>new(generation,policyGeneration);
 public void Invalidate()=>generation++;
 public void Dispose(){disposed=true;Invalidate();}
 public bool IsCurrent(NavigationLease lease,long policyGeneration)=>!disposed&&lease.TabGeneration==generation&&lease.PolicyGeneration==policyGeneration;
}
/// <summary>All live private controls share a session; final retirement creates a fresh profile identity.</summary>
public sealed class PrivateSessionIdentity
{
 public string Name {get;private set;}=FreshName();
 public void Retire()=>Name=FreshName();
 private static string FreshName()=>"OptimusPrivate"+Guid.NewGuid().ToString("N");
}
