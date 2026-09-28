# Runtime image: Amazon Corretto 21 (LTS) provides the JDK that runs the
# Spring Boot fat jar produced by `mvn clean package`.
FROM amazoncorretto:21

WORKDIR /app

# The jar must be built on the host first (mvn clean package).
COPY target/*.jar app.jar

# Inside the container the application listens on 9000. Override it at run
# time with `-e PORT=<port>` if needed.
ENV PORT=9000

EXPOSE 9000

ENTRYPOINT ["java", "-jar", "app.jar"]
