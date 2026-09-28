import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Minimal closed-loop HTTP load generator (JDK only, no dependencies).
 *
 * <p>Usage: {@code java scripts/LoadTest.java <url> [concurrency] [seconds]}
 *
 * <p>Each virtual thread sends a request, waits for the response and sends
 * the next one. After a 10 s warm-up it reports throughput and latency
 * percentiles, which are used to size EC2 instances in the cost analysis.
 */
public class LoadTest {

    public static void main(String[] args) throws Exception {
        URI uri = URI.create(args[0]);
        int concurrency = args.length > 1 ? Integer.parseInt(args[1]) : 16;
        int seconds = args.length > 2 ? Integer.parseInt(args[2]) : 30;

        HttpClient client = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        HttpRequest request = HttpRequest.newBuilder(uri).GET().build();

        run(client, request, concurrency, 10, false);
        run(client, request, concurrency, seconds, true);
    }

    private static void run(HttpClient client, HttpRequest request,
            int concurrency, int seconds, boolean report) throws Exception {
        long end = System.nanoTime() + Duration.ofSeconds(seconds).toNanos();
        AtomicLong errors = new AtomicLong();
        List<List<Long>> latencies = new ArrayList<>();

        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < concurrency; i++) {
                List<Long> own = new ArrayList<>();
                latencies.add(own);
                executor.submit(() -> {
                    while (System.nanoTime() < end) {
                        long start = System.nanoTime();
                        try {
                            HttpResponse<String> response =
                                    client.send(request, HttpResponse.BodyHandlers.ofString());
                            if (response.statusCode() != 200) {
                                errors.incrementAndGet();
                            }
                        } catch (Exception e) {
                            errors.incrementAndGet();
                        }
                        own.add(System.nanoTime() - start);
                    }
                    return null;
                });
            }
        }

        if (!report) {
            return;
        }
        List<Long> all = new ArrayList<>();
        latencies.forEach(all::addAll);
        Collections.sort(all);
        System.out.printf("url=%s concurrency=%d duration=%ds%n", request.uri(), concurrency, seconds);
        System.out.printf("requests=%d errors=%d throughput=%.1f req/s%n",
                all.size(), errors.get(), all.size() / (double) seconds);
        System.out.printf("latency ms: p50=%.1f p95=%.1f p99=%.1f max=%.1f%n",
                percentile(all, 50), percentile(all, 95), percentile(all, 99),
                all.get(all.size() - 1) / 1e6);
    }

    private static double percentile(List<Long> sorted, int p) {
        int index = (int) Math.ceil(p / 100.0 * sorted.size()) - 1;
        return sorted.get(Math.max(index, 0)) / 1e6;
    }
}
