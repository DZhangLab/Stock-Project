package com.summer.stockproject;

import com.summer.stockproject.login.dao.UserRepository;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;

@SpringBootApplication
public class StockprojectApplication {

	public static void main(String[] args) {
		SpringApplication.run(StockprojectApplication.class, args);
	}

}
