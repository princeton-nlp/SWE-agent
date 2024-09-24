FROM ubuntu:16.04

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y apache2 libapache2-mod-perl2 build-essential
RUN cpan install CGI
RUN a2enmod cgi

RUN echo "Listen 8000" >> /etc/apache2/ports.conf
COPY ./000-default.conf /etc/apache2/sites-available/
COPY ./index.html /var/www/html

COPY ./cgi /var/www/cgi-bin
RUN chmod +x /var/www/cgi-bin/*

COPY ./flag /

RUN service apache2 stop

EXPOSE 8000
CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]
