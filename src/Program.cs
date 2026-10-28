using KoikatuMCP.Logging;
using KoikatuMCP.Services;
using KoikatuMCP.Tools;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

// Streamable HTTP endpoint; override with KOIKATUMCP_URL, e.g. http://0.0.0.0:8766
var url = Environment.GetEnvironmentVariable("KOIKATUMCP_URL") ?? "http://0.0.0.0:8766";

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddMcpServer()
    .WithHttpTransport()
    .WithToolsFromAssembly();

builder.Services.AddTransient<WebSocketService>();

builder.Logging.AddConsole(options =>
{
    options.LogToStandardErrorThreshold = LogLevel.Debug;
});

// Add custom file logging with Debug level
builder.Logging.AddProvider(new FileLoggerProvider(LogLevel.Information));
builder.Logging.SetMinimumLevel(LogLevel.Information);

var app = builder.Build();

app.MapMcp();

app.Run(url);
