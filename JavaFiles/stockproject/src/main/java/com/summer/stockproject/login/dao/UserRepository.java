package com.summer.stockproject.login.dao;

import com.summer.stockproject.login.Entity.User;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserRepository extends JpaRepository<User, String> {

    User getReferenceById(String email);
}
