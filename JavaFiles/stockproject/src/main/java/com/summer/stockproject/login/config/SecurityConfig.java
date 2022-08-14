package com.summer.stockproject.login.config;

import com.summer.stockproject.login.service.AuthenticationService;
import com.summer.stockproject.login.service.HashService;
import com.summer.stockproject.login.service.UserDetailsServiceImpl;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.authentication.builders.AuthenticationManagerBuilder;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configuration.WebSecurityConfigurerAdapter;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.NoOpPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

@Configuration
@EnableWebSecurity
public class SecurityConfig  extends WebSecurityConfigurerAdapter {
    private AuthenticationService authenticationService;

    private HashService hashService;

    @Autowired
    public SecurityConfig(AuthenticationService authenticationService, HashService hashService) {
        this.hashService = hashService;
        this.authenticationService = authenticationService;
    }

    @Bean
    public UserDetailsService userDetailsService() {
        return new UserDetailsServiceImpl();
    }

    @Override
    protected void configure(AuthenticationManagerBuilder auth) throws Exception {
        auth.authenticationProvider(this.authenticationService);

    }

    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.authorizeRequests()
                .antMatchers("/jsFile?**","/signup").permitAll()
             //   .antMatchers("/").hasRole("user")
                .antMatchers("/graph/admin").hasAuthority("admin")
                .anyRequest().authenticated().and()
                .logout().permitAll();
        http.formLogin()
                .loginPage("/login")
                .permitAll();

    }



}
