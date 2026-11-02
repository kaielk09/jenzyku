import java.io.IOException;
import java.net.URI;
import java.nio.file.*;
import java.util.Locale;

/**
 * 321code Java bootstrapper.
 * Run with: java Install321.java
 * Requires Java 11+ and Windows.
 */
public class Install321 {
    private static final String INSTALLER_URL =
        "https://raw.githubusercontent.com/kaielk09/jenzyku/main/321code-Setup.exe";

    public static void main(String[] args) throws Exception {
        String os = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);
        if (!os.contains("win")) {
            System.err.println("Ten instalator uruchamia instalator 321code dla Windows.");
            System.err.println("Uruchom go na komputerze z systemem Windows.");
            System.exit(1);
        }

        Path installer = Files.createTempFile("321code-setup-", ".exe");
        installer.toFile().deleteOnExit();

        System.out.println("Pobieranie instalatora 321code z GitHuba...");
        try {
            var client = java.net.http.HttpClient.newBuilder()
                .followRedirects(java.net.http.HttpClient.Redirect.NORMAL)
                .build();
            var request = java.net.http.HttpRequest.newBuilder()
                .uri(URI.create(INSTALLER_URL))
                .GET()
                .build();
            var response = client.send(
                request,
                java.net.http.HttpResponse.BodyHandlers.ofFile(installer)
            );
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new IOException("GitHub zwrocil HTTP " + response.statusCode());
            }
        } catch (Exception ex) {
            Files.deleteIfExists(installer);
            throw new IOException("Nie udalo sie pobrac instalatora 321code.", ex);
        }

        System.out.println("Uruchamianie instalatora. Kliknij przycisk Zainstaluj.");
        new ProcessBuilder(installer.toAbsolutePath().toString())
            .inheritIO()
            .start();
    }
}
